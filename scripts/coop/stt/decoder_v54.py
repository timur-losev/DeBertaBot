"""The slow path for the long tail (HANDOFF.md, "brains", tier 2): a small instruction-tuned decoder reads the lines the
classifier is unsure about, with the intent list and a few seed commands per intent in its prompt, and names the intent.
Is it right more often than the classifier's own under-threshold pick, and what does it cost on the CPU?

Scored with the teacher ensemble's out-of-fold probabilities (kd54_teacher_s*.json): the under-threshold lines are the
ones the bot would ask again about; the decoder's pick on them is compared with the classifier's pick (below the
threshold, as if the gate were off) and with the truth. The decoder is scored by constrained choice: the label whose
log-probability as the continuation of the prompt is highest (no free generation, nothing to parse).

    python decoder_v54.py Qwen/Qwen2.5-1.5B-Instruct [--cond vctkB] [--device cuda|cpu] [--limit N] [--timing]
"""
import io, json, os, sys, time
os.environ["COOP_TAG"] = "v54"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import coop_v2 as V

name = sys.argv[1]
args = sys.argv[2:]
cond = args[args.index("--cond") + 1] if "--cond" in args else "vctkB"
device = args[args.index("--device") + 1] if "--device" in args else ("cuda" if torch.cuda.is_available() else "cpu")
limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 0
timing = "--timing" in args
items = {i["id"]: i for i in V.load_items() if i["maj"]}
seeds = V.seed_items()
spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731

# ---- the teacher ensemble's out-of-fold picks, gate and threshold as score_v54.py fits them
runs = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2)]
probs = {}
for r in runs:
    for f in r.values():
        for k, v in f["test"].items():
            probs.setdefault(k, []).append(v)
n_seeds = max(len(v) for v in probs.values())
probs = {k: [sum(x[j] for x in v) / len(v) for j in range(len(V.INTENTS))] for k, v in probs.items() if len(v) == n_seeds}
print(f"teacher files: {n_seeds} seeds per line, {len(probs)} test rows (a partial run until all 15 fold teachers are done)")


def by(c):
    return {k.split("|", 1)[1]: v for k, v in probs.items() if k.split("|", 1)[0] == c and spoken(items[k.split("|", 1)[1]])}


best = None
for gate in ("top", "family"):
    for t in range(0, 100, 2):
        near = cross = 0
        for c in ("clean", "kokoro", "kokorox", "vctkA"):
            p = by(c)
            s = V.score(V.picks(p, gate, t / 100), [items[k] for k in p])
            near += s["near_count"]; cross += s["cross_count"]
        v = near - 2 * cross
        if best is None or v > best[0] or (v == best[0] and gate == "top"):
            best = (v, gate, t / 100)
_, gate, thr = best
p_cond = by(cond)
heard = {k.split("|", 1)[1]: None for k in probs if k.startswith(cond + "|")}
# the text as heard under the condition: from the build's transcripts
import build_v54 as B  # noqa: E402
text_of = B.heard(cond) if cond != "typed" else {k: items[k]["text"] for k in items}
unsure = [k for k in p_cond if V.pick(p_cond[k], gate, 0.0)[1] < thr]
if limit:
    unsure = unsure[:limit]
print(f"teacher ensemble OOF, gate {gate}, threshold {thr:.2f}; {cond}: {len(p_cond)} lines, {len(unsure)} under the threshold")

# ---- the prompt: the intents with a short gloss and two seeds each
glosses = {k: v.get("description", v.get("label", k)) for k, v in V.I.items()}
by_intent = {}
for s in seeds:
    by_intent.setdefault(s["maj"], []).append(s["text"])
menu = "\n".join(f"- {k}: {glosses[k]}. e.g. " + " / ".join(f'"{t}"' for t in by_intent.get(k, [])[:2]) for k in V.INTENTS)
SYSTEM = ("You classify what a player says to an AI teammate in a tactical co-op shooter into exactly one intent. "
          "The line is a speech-to-text transcript and may be garbled. Answer with the intent name only.\n\nIntents:\n" + menu)

tok = AutoTokenizer.from_pretrained(name)
model = AutoModelForCausalLM.from_pretrained(name, dtype=torch.float32 if device == "cpu" else torch.bfloat16).to(device).eval()
if device == "cpu":
    torch.set_num_threads(4)
import copy  # noqa: E402
label_ids = [tok(k, add_special_tokens=False)["input_ids"] for k in V.INTENTS]
L = max(map(len, label_ids))
LAB = torch.full((len(label_ids), L), tok.pad_token_id or 0, dtype=torch.long)
LAB_MASK = torch.zeros((len(label_ids), L), dtype=torch.long)
for r, ids in enumerate(label_ids):
    LAB[r, :len(ids)] = torch.tensor(ids)
    LAB_MASK[r, :len(ids)] = 1
LAB, LAB_MASK = LAB.to(device), LAB_MASK.to(device)

# the system prompt is the same for every line: its KV cache is computed once and copied per line, so a line costs
# its own ~20 tokens plus one batched forward of the 41 labels (what a game would do too)
_sys_prefix = tok.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": "X"}], add_generation_prompt=True, tokenize=False)
_sys_prefix = _sys_prefix[:_sys_prefix.index("<|im_start|>user")]
SYS_IDS = tok(_sys_prefix, add_special_tokens=False)["input_ids"]
with torch.no_grad():
    SYS_CACHE = model(input_ids=torch.tensor([SYS_IDS], device=device), use_cache=True).past_key_values


@torch.no_grad()
def choose(line):
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f'Player said: "{line}"\nIntent:'}]
    pid = tok(tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False), add_special_tokens=False)["input_ids"]
    assert pid[:len(SYS_IDS)] == SYS_IDS, "the system prompt is not a token prefix of the full prompt"
    rest = pid[len(SYS_IDS):]
    cache = copy.deepcopy(SYS_CACHE)
    out = model(input_ids=torch.tensor([rest], device=device), past_key_values=cache, use_cache=True)
    first_logp = torch.log_softmax(out.logits[0, -1].float(), -1)
    n = len(label_ids)
    cache = out.past_key_values
    cache.batch_repeat_interleave(n)
    plen = len(pid)
    mask = torch.cat([torch.ones((n, plen), dtype=torch.long, device=device), LAB_MASK], 1)
    o2 = model(input_ids=LAB, attention_mask=mask, past_key_values=cache, use_cache=False)
    lps = torch.log_softmax(o2.logits.float(), -1)   # [n, L, vocab]: position j predicts label token j+1
    scores = []
    for r, ids in enumerate(label_ids):
        lp = first_logp[ids[0]].item()
        for j in range(1, len(ids)):
            lp += lps[r, j - 1, ids[j]].item()
        scores.append(lp)
    j = max(range(len(scores)), key=scores.__getitem__)
    return V.INTENTS[j]


t0 = time.time()
dec, cls = {}, {}
lat = []
for n, k in enumerate(unsure):
    line = text_of[k]
    t1 = time.perf_counter()
    dec[k] = choose(line)
    lat.append(time.perf_counter() - t1)
    cls[k] = V.pick(p_cond[k], gate, 0.0)[0]
    if timing and n >= 20:
        break
sub = [items[k] for k in dec]
s_dec = V.score(dec, sub)
s_cls = V.score(cls, sub)
s_none = V.score({k: "NONE" for k in dec}, sub)
print(f"{name} on {len(sub)} under-threshold {cond} lines ({device}; {sum(lat) / len(lat) * 1000:.0f} ms per line, "
      f"p95 {sorted(lat)[int(0.95 * (len(lat) - 1))] * 1000:.0f} ms):")
for what, s in (("decoder", s_dec), ("classifier's pick, gate off", s_cls), ("asking again (the bot today)", s_none)):
    print(f"  {what:30s} near {100 * s['near']:5.1f}  wrong family {100 * s['cross']:5.1f}%  acts on non-order {100 * s['fired_on_nonorder']:5.1f}%  criterion {100 * (s['near'] - 2 * s['cross']):6.1f}")
json.dump({"model": name, "cond": cond, "gate": gate, "threshold": thr, "n": len(sub), "ms": sum(lat) / len(lat) * 1000, "device": device,
           "picks": {k: {"text": text_of[k], "truth": items[k]["maj"], "decoder": dec[k], "classifier": cls[k]} for k in dec}},
          io.open(os.path.join(HERE, f"decoder54_{name.split('/')[-1]}_{cond}_{device}.json"), "w", encoding="utf-8"), indent=1)
