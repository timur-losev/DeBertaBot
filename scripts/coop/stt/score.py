"""The whole chain on the synthesized lines: speech-to-text output -> the v31 bot -> the project's criterion.
Run in the jev environment (torch). Reads out_<engine>_<cond>.json, writes score.json. Nothing touches the repository:
Bot.classify is used, which does not write the bot's log."""
import glob, io, json, os, re, sys
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
os.chdir(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
torch.set_num_threads(6)
import coop_v2 as V
import coop_bot as B

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(io.open(os.path.join(HERE, "lines.json"), encoding="utf-8"))
items = {i["id"]: i for i in V.load_items()}
ref = {r["id"]: r["text"] for r in rows}
bot = B.Bot()
assert bot.gate == "family"
DOMAIN = ["breach", "rappel", "frag", "flash", "smoke", "drone", "defuse", "plant", "flank", "vault", "revive", "nade"]
cache = {}


def infer(texts):
    """The bot's own computation (softmax per member, mean), batched on the GPU so the CPU stays free."""
    todo = [t for t in dict.fromkeys(texts) if t not in cache]
    for m in bot.models:
        m.to("cuda")
    for b in range(0, len(todo), 64):
        x = bot.tok(todo[b:b + 64], truncation=True, max_length=64, padding=True, return_tensors="pt").to("cuda")
        with torch.no_grad():
            p = torch.stack([torch.softmax(m(**x).logits.float(), -1) for m in bot.models]).mean(0).cpu().tolist()
        cache.update(zip(todo[b:b + 64], p))


def probs(text):
    return cache[text]


def words(t):
    return re.findall(r"[a-z0-9']+", t.lower())


def wer(pairs):
    err = n = 0
    for r, h in pairs:
        r, h = words(r), words(h)
        d = list(range(len(h) + 1))
        for i in range(1, len(r) + 1):
            prev, d[0] = d[0], i
            for j in range(1, len(h) + 1):
                prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
        err += d[len(h)]; n += len(r)
    return err / max(n, 1)


def evaluate(texts):
    """texts: id -> what the bot is given. Strict project scoring at the bot's own gate and threshold."""
    infer(texts.values())
    its = [items[k] for k in texts]
    picks = {k: V.pick(probs(t), bot.gate, bot.threshold)[0] for k, t in texts.items()}
    s = V.score(picks, its)
    return {"near": 100 * s["near"], "cross": 100 * s["cross"], "fired": 100 * s["fired_on_nonorder"],
            "criterion": 100 * (s["near"] - 2 * s["cross"]), "cross_count": s["cross_count"], "picks": picks}


lower = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()
out = {}
base = evaluate(ref)
base_low = evaluate({k: lower(t) for k, t in ref.items()})
out["typed text (no speech)"] = {"clean": {"raw": base, "lower": base_low}}
print(f"typed text: near {base['near']:.1f} wrong-family {base['cross']:.1f}% criterion {base['criterion']:.1f} | lowercased: "
      f"near {base_low['near']:.1f} wrong-family {base_low['cross']:.1f}% criterion {base_low['criterion']:.1f}")
for path in sorted(glob.glob(os.path.join(HERE, "out_*_*.json"))):
    name = os.path.basename(path)[4:-5]
    if name.endswith("_t") or "_lat" in name:
        continue
    engine, cond = name.rsplit("_", 1)
    d = json.load(io.open(path, encoding="utf-8"))
    hyp = {r["id"]: r["text"] for r in d["rows"]}
    res = {"raw": evaluate(hyp), "lower": evaluate({k: lower(t) for k, t in hyp.items()})}
    res["wer"] = 100 * wer([(ref[k], hyp[k]) for k in hyp])
    dom = [(w, k) for k in hyp for w in DOMAIN if w in words(ref[k])]
    res["domain_kept"] = 100 * sum(w in words(hyp[k]) for w, k in dom) / max(len(dom), 1)
    res["domain_n"] = len(dom)
    res["empty"] = sum(not hyp[k].strip() for k in hyp)
    # the lines whose intent family survives typed -> spoken, with the lowercased text
    same = sum(V.FAMILY[res["lower"]["picks"][k]] == V.FAMILY[base_low["picks"][k]] for k in hyp)
    res["same_family_as_typed"] = 100 * same / len(hyp)
    out.setdefault(engine, {})[cond] = res
    print(f"{engine:22s} {cond:5s} WER {res['wer']:5.1f}  domain words kept {res['domain_kept']:5.1f}%  | raw: near {res['raw']['near']:5.1f} "
          f"wf {res['raw']['cross']:4.1f}% crit {res['raw']['criterion']:5.1f} | lower: near {res['lower']['near']:5.1f} "
          f"wf {res['lower']['cross']:4.1f}% crit {res['lower']['criterion']:5.1f} | same family as typed {res['same_family_as_typed']:5.1f}%")
for e in out.values():
    for c in e.values():
        for k in ("raw", "lower"):
            c[k].pop("picks", None)
json.dump(out, io.open(os.path.join(HERE, "score.json"), "w", encoding="utf-8"), indent=1)
