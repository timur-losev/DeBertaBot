"""Lines with several orders (the chains study, after qlora_v54.py): can the taught decoder list the orders of a line in
the order the bot must carry them out? The classifier gives one intent per line by construction, and its data reads a
line that way (11 of 1215 lines have a " then "). The rules for reading a line as a list are chains/spec_chain.json.

Everything is on fold 0 of distill_v54.py's split, so a held-out line is unseen typed, spoken, and inside a joined line.

Training rows
  singles    the fold's training rows as they are (the answer is one intent), without the lines with " then " in
             them: under spec_chain.json some of those are two orders
  composed   N_COMPOSED lines made of two or three single ORDER lines of the fold's training side (typed, or as
             Parakeet heard them) put into one of JOIN_TRAIN's patterns; the answer is the parts' intents in the
             order of execution. No WAIT or GO_NOW among the parts: "wait, then X" reads as X's timing
  teacher    chains/teacher_lines.json: natural lines a teacher model wrote, each with its orders and with every
             order said alone (its "pieces"). A line is kept if the v54 ensemble reads every piece as the teacher
             labelled it (`check`: the classifier as the teacher's calculator); TEACHER_COPIES copies of each
Variants: composed (singles + composed) and teacher (the same and the teacher's kept lines).

Tests
  singles    the fold's held-out rows: the answer must stay one intent
  joined     held-out typed lines in the TRAINING patterns
  unseen     held-out typed lines in JOIN_TEST's patterns, which no training line has
  heard      the same from what Parakeet heard of the held-out lines read by unseen voices (VCTK pool B)
  blind      chains/blind_author.json, natural lines by a blind author, read by two blind annotators
             (blind_ann1.json, blind_ann2.json); the truth is the list two of the three give, the rest is left out

    python chains_v54.py check                the teacher's pieces, and the blind lines, read by the v54 ensemble
                                              -> chains/teacher_checked.json, chains/blind_bot.json
    python chains_v54.py train VARIANT SEED   an adapter -> models/coop-qwen3-qlora-chains-v54/<VARIANT>_seed<SEED>,
                                              its answers on every test -> chains54_<VARIANT>_s<SEED>.json
    python chains_v54.py answer VARIANT SEED  the answers again from the saved adapter (after the blind set is complete)
    python chains_v54.py score [--wrong]      the tables; --wrong lists the blind lines a variant misses
"""
import io, json, os, random, sys, time
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import torch
import qlora_v54 as Q
from qlora_v54 import B, D, T, V

NAME = "qwen3"
CH = os.path.join(HERE, "chains")
BOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v54"))
SYSTEM = ("You are the AI teammate in a tactical co-op shooter. The player's line is a speech-to-text transcript and "
          "may be garbled. Answer with the names of the orders it gives, in the order you must carry them out, "
          f"separated by '{Q.SEP.strip()}', or NONE.")
# fixed before any chain line was read: the patterns, the sizes, the copies
N_COMPOSED, TEACHER_COPIES, N_TEST, MAX_PART = 3000, 3, 400, 60
NOT_PART = {"NONE", "YES", "NO", "MAYBE", "DONT_KNOW", "WAIT", "GO_NOW"}
# a, b, c are in the order of execution
JOIN_TRAIN = [
    "{a}, then {b}", "{a} then {b}", "{a} and then {b}", "{a} and {b}", "{a}, {b}", "{a}. {b}", "{a} {b}",
    "{a}, after that {b}", "{a} and after that {b}", "first {a}, then {b}", "{a}, and when that's done {b}",
    "{a}, next {b}", "{a} and {b} right after",
    "{b}, but first {a}", "before you {b}, {a}", "{b} after you {a}",
    "{a}, {b}, then {c}", "{a} then {b} then {c}", "{a}, {b} and {c}", "first {a}, then {b}, and then {c}",
    "{a} and {b}, after that {c}", "{a} {b} {c}", "{a}. {b}. {c}", "{a}, then {b}, and after that {c}",
    "{a}, and before you {c}, {b}",
]
JOIN_TEST = [
    "{a}, and afterwards {b}", "{a} and right after that {b}", "{a}, once that's done {b}", "{a} and from there {b}",
    "{a}; {b}", "{a} okay and {b}",
    "{b}, but {a} first", "{b} as soon as you {a}",
    "{a}, and afterwards {b}, and finally {c}", "{a} {b} and lastly {c}", "{a}, once that's done {b}, and from there {c}",
    "{c}, but before that {a} and {b}",
]
assert not set(JOIN_TRAIN) & set(JOIN_TEST)


def has_then(t):
    return " then " in f" {t.lower()} "


def tidy(t, first):
    """A part without its final punctuation; a part that does not open the line loses its capital."""
    t = t.strip().rstrip(".!?,;").strip()
    if first or len(t) < 2 or not t[1].islower() or t.split()[0] in ("I", "I'm", "I'll", "I've"):
        return t
    return t[0].lower() + t[1:]


def compose(pool, patterns, n, rng, tag):
    out, seen = [], set()
    while len(out) < n:
        m = 2 if rng.random() < 0.7 else 3
        pat = rng.choice([p for p in patterns if p.count("{") == m])
        parts = rng.sample(pool, m)
        text = pat.format(**{k: tidy(p["text"], pat.startswith("{" + k + "}")) for k, p in zip("abc", parts)})
        if text not in seen:
            seen.add(text)
            out.append({"id": f"{tag}_{len(out)}", "text": text, "orders": [p["maj"] for p in parts], "join": pat})
    return out


def part_ok(r):
    return r["maj"] not in NOT_PART and not has_then(r["text"]) and len(r["text"]) <= MAX_PART


def blind():
    """The blind lines with the list two of the three readers give (None where no two agree)."""
    paths = [os.path.join(CH, f) for f in ("blind_author.json", "blind_ann1.json", "blind_ann2.json")]
    if not all(map(os.path.exists, paths)):
        return []
    auth, a1, a2 = (json.load(io.open(p, encoding="utf-8")) for p in paths)
    out = []
    for a in auth:
        reads = [tuple(a["orders"]), tuple(a1[a["id"]]), tuple(a2[a["id"]])]
        top, n = Counter(reads).most_common(1)[0]
        out.append({"id": a["id"], "voice": a["voice"], "text": a["text"], "orders": list(top) if n >= 2 else None, "unanimous": n == 3})
    return out


def training(variant):
    rows, _ = D.folds()[0]
    singles = [r for r in rows if not has_then(r["text"])]
    out = [{"text": r["text"], "orders": [r["maj"]]} for r in singles]
    out += compose([r for r in singles if part_ok(r)], JOIN_TRAIN, N_COMPOSED, random.Random(1001), "c")
    counts = {"singles": len(singles), "composed": N_COMPOSED, "teacher": 0}
    if variant == "teacher":
        kept = [t for t in json.load(io.open(os.path.join(CH, "teacher_checked.json"), encoding="utf-8")) if t["kept"]]
        out += TEACHER_COPIES * [{"text": t["text"], "orders": t["orders"]} for t in kept]
        counts["teacher"] = len(kept)
    return out, counts


def tests():
    _, test = D.folds()[0]
    items = {i["id"]: i for i in B.LINES}
    held = sorted({r["id"].split("|", 1)[1] for r in test})
    typed = [{"text": items[k]["text"], "maj": items[k]["maj"]} for k in held]
    heard = [{"text": B.heard("vctkB")[k], "maj": items[k]["maj"]} for k in held if k in B.SPOKEN]
    return {"singles": [{"id": r["id"], "text": r["text"]} for r in test],
            "joined": compose(list(filter(part_ok, typed)), JOIN_TRAIN, N_TEST, random.Random(2001), "joined"),
            "unseen": compose(list(filter(part_ok, typed)), JOIN_TEST, N_TEST, random.Random(2002), "unseen"),
            "heard": compose(list(filter(part_ok, heard)), JOIN_TEST, N_TEST, random.Random(2003), "heard"),
            "blind": blind()}


@torch.no_grad()
def generate(model, turns, texts, rows=64, max_new=28):
    """Greedy answers, free running (no grammar): a game would constrain the decoding to the names, here an answer
    that is not a list of names is counted as wrong."""
    model.eval()
    out = []
    for b in range(0, len(texts), rows):
        prompts = [turns.prompt(t) for t in texts[b:b + rows]]
        n = max(map(len, prompts))
        x = torch.full((len(prompts), n), turns.pad, dtype=torch.long)
        m = torch.zeros((len(prompts), n), dtype=torch.long)
        for r, p in enumerate(prompts):                   # padded on the left: every prompt ends where the answer starts
            x[r, n - len(p):] = torch.tensor(p)
            m[r, n - len(p):] = 1
        with torch.autocast("cuda", dtype=torch.bfloat16):
            y = model.generate(input_ids=x.to(Q.DEVICE), attention_mask=m.to(Q.DEVICE), max_new_tokens=max_new, do_sample=False,
                               eos_token_id=turns.end, pad_token_id=turns.pad)
        for row in y[:, n:].tolist():
            out.append(turns.tok.decode(row[:row.index(turns.end)] if turns.end in row else row))
    return out


def adapter_dir(variant, seed):
    return os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", f"coop-{NAME}-qlora-chains-v54", f"{variant}_seed{seed}"))


def answers(model, turns, variant, seed, extra):
    t0 = time.time()
    pred = {name: dict(zip([t["id"] for t in ts], generate(model, turns, [t["text"] for t in ts]))) for name, ts in tests().items()}
    json.dump({"variant": variant, "seed": seed, **extra, "answer_s": round(time.time() - t0), "pred": pred},
              io.open(os.path.join(HERE, f"chains54_{variant}_s{seed}.json"), "w", encoding="utf-8"), indent=1)
    print(f"chains {variant} seed {seed}: " + ", ".join(f"{k} {len(v)}" for k, v in pred.items()) + f" answered in {time.time() - t0:.0f}s", flush=True)


def train(variant, seed):
    t0 = time.time()
    rows, counts = training(variant)
    model, turns = Q.train(NAME, rows, seed, Q.TAGS["r16"], system=SYSTEM, checkpoint=True)
    d = adapter_dir(variant, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "train_s": round(time.time() - t0)}
    json.dump({"base": Q.MODELS[NAME], **Q.TAGS["r16"], "system": SYSTEM, "sep": Q.SEP, **extra}, io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1)
    print(f"chains {variant} seed {seed}: {counts}, trained in {time.time() - t0:.0f}s", flush=True)
    answers(model, turns, variant, seed, extra)


def answer(variant, seed):
    from peft import PeftModel
    model, tok = Q.load(NAME)
    model = PeftModel.from_pretrained(model, adapter_dir(variant, seed))
    old = json.load(io.open(os.path.join(HERE, f"chains54_{variant}_s{seed}.json"), encoding="utf-8"))
    answers(model, Q.Turns(tok, SYSTEM), variant, seed, {"rows": old["rows"], "train_s": old["train_s"]})


def bot_picks(rows, members=None):
    """id -> (pick, confidence) of the v54 ensemble, with its own gate and threshold, on the text as the bot gets it.
    members: other member folders to read with (chains2_v54.py: the fold's own teachers), under the same gate."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    cfg = json.load(io.open(os.path.join(BOT, "bot_config.json"), encoding="utf-8"))
    rows = [{"id": r["id"], "text": B.norm(r["text"])} for r in rows]
    runs = []
    for m in members or [os.path.join(BOT, m) for m in cfg["members"]]:
        tok = AutoTokenizer.from_pretrained(m)
        model = AutoModelForSequenceClassification.from_pretrained(m, dtype=torch.float32).to(D.DEVICE)
        runs.append(D.predict(model, tok, rows, D.DEVICE))
        del model
        T.free_cache(D.DEVICE)
    probs = {r["id"]: [sum(run[r["id"]][j] for run in runs) / len(runs) for j in range(len(V.INTENTS))] for r in rows}
    return {k: (V.pick(p, cfg["gate"], cfg["threshold"])[0], V.pick(p, cfg["gate"], 0.0)) for k, p in probs.items()}, cfg


def check():
    lines = json.load(io.open(os.path.join(CH, "teacher_lines.json"), encoding="utf-8"))
    for t in lines:
        assert len(t["orders"]) == len(t["pieces"]) and set(t["orders"]) <= set(V.INTENTS), t["id"]
    picks, cfg = bot_picks([{"id": f"{t['id']}#{k}", "text": p} for t in lines for k, p in enumerate(t["pieces"])])
    n_piece = n_agree = n_unsure = 0
    confusions = Counter()
    for t in lines:
        got = [picks[f"{t['id']}#{k}"] for k in range(len(t["pieces"]))]
        t["classifier"] = [g[0] for g in got]
        t["unsure"] = [g[0] == "NONE" and g[1][0] != "NONE" for g in got]     # under the threshold: the bot would ask again
        t["kept"] = t["classifier"] == t["orders"]
        for want, g, u in zip(t["orders"], got, t["unsure"]):
            n_piece += 1
            n_agree += g[0] == want
            n_unsure += u and want != "NONE"
            if g[0] != want:
                confusions[(want, f"unsure, would be {g[1][0]}" if u else g[0])] += 1
    json.dump(lines, io.open(os.path.join(CH, "teacher_checked.json"), "w", encoding="utf-8"), indent=1)
    kept = [t for t in lines if t["kept"]]
    print(f"the teacher's {len(lines)} lines, {n_piece} pieces, read by the v54 ensemble (gate {cfg['gate']}, threshold {cfg['threshold']}):")
    print(f"  pieces the classifier reads as the teacher labelled them: {n_agree} ({100 * n_agree / n_piece:.1f}%); "
          f"of the {n_piece - n_agree} others, {n_unsure} are under the threshold")
    print(f"  lines kept (every piece agrees): {len(kept)} ({100 * len(kept) / len(lines):.1f}%)")
    for what, key in (("orders in the line", lambda t: min(len(t["orders"]), 3)), ("voice", lambda t: t["voice"])):
        groups = sorted({key(t) for t in lines})
        print(f"  kept by {what}: " + ", ".join(f"{g}{'+' if g == 3 else ''}: {sum(key(t) == g for t in kept)}/{sum(key(t) == g for t in lines)}" for g in groups))
    print("  the commonest disagreements (teacher -> classifier): " + "; ".join(f"{a} -> {b} x{n}" for (a, b), n in confusions.most_common(14)))
    p = os.path.join(CH, "blind_author.json")
    if os.path.exists(p):
        picks, _ = bot_picks(json.load(io.open(p, encoding="utf-8")))
        json.dump({k: [v[0], v[1][0], round(v[1][1], 3)] for k, v in picks.items()}, io.open(os.path.join(CH, "blind_bot.json"), "w", encoding="utf-8"), indent=1)
        print(f"  the blind lines read by the same bot: {len(picks)} -> chains/blind_bot.json")


def parse(s):
    return [x.strip() for x in s.split(Q.SEP.strip())]


def score(wrong=False):
    ts = tests()
    items = {i["id"]: i for i in B.LINES}
    bl = [t for t in ts["blind"] if t["orders"]]
    if ts["blind"]:
        print(f"blind lines: {len(ts['blind'])}, two of three readers agree on {len(bl)}, all three on {sum(t['unanimous'] for t in ts['blind'])}; "
              f"by number of orders: " + ", ".join(f"{n}: {sum(len(t['orders']) == n for t in bl)}" for n in sorted({len(t['orders']) for t in bl})))

    def chain_row(label, rows, pred):
        if not rows:
            return
        got = [parse(pred[t["id"]]) for t in rows]
        exact = sum(g == t["orders"] for g, t in zip(got, rows))
        bag = sum(sorted(g) == sorted(t["orders"]) for g, t in zip(got, rows))
        count = sum(len(g) == len(t["orders"]) for g, t in zip(got, rows))
        bad = sum(not set(g) <= set(V.INTENTS) for g in got)
        print(f"  {label:52s} {len(rows):5d} {100 * exact / len(rows):7.1f} {100 * bag / len(rows):9.1f} {100 * count / len(rows):12.1f} {bad:9d}")

    def single_row(label, cond, pick_of):
        """near / wrong family as coop_v2.score counts them, no threshold; an answer that is not one intent is wrong."""
        ids = [t["id"] for t in ts["singles"] if t["id"].split("|", 1)[0] == cond]
        near = cross = one = 0
        for k in ids:
            it, p = items[k.split("|", 1)[1]], pick_of(k)
            one += len(p) == 1
            good = len(p) == 1 and p[0] in V.FAMILY and (p[0] in it["accept"] or V.FAMILY[p[0]] == V.FAMILY[it["maj"]])
            near += good
            cross += not good and p != ["NONE"]
        print(f"  {label:52s} {len(ids):5d} {100 * one / len(ids):11.1f} {100 * near / len(ids):6.1f} {100 * cross / len(ids):9.1f}% {100 * (near - 2 * cross) / len(ids):10.1f}")

    files = sorted(f for f in os.listdir(HERE) if f.startswith("chains54_") and f.endswith(".json"))
    for fn in files:
        r = json.load(io.open(os.path.join(HERE, fn), encoding="utf-8"))
        pred = r["pred"]
        print(f"\nvariant {r['variant']}, seed {r['seed']}: {r['rows']['singles']} single rows + {r['rows']['composed']} composed + "
              f"{r['rows']['teacher']} teacher lines x{TEACHER_COPIES}, {r['train_s']} s of training")
        print(f"  {'lines with several orders':52s} {'n':>5s} {'exact':>7s} {'same set':>9s} {'right count':>12s} {'not names':>9s}")
        chain_row("held-out lines, training patterns", ts["joined"], pred["joined"])
        chain_row("held-out lines, unseen patterns", ts["unseen"], pred["unseen"])
        chain_row("  of them, the second order said first", [t for t in ts["unseen"] if t["join"].startswith(("{b}", "{c}"))], pred["unseen"])
        chain_row("held-out lines heard from unseen voices, unseen patterns", ts["heard"], pred["heard"])
        if bl and pred.get("blind"):
            chain_row("blind natural lines", bl, pred["blind"])
            for n, label in ((1, "  one order"), (2, "  two orders"), (3, "  three or four orders")):
                chain_row(label, [t for t in bl if min(len(t["orders"]), 3) == n], pred["blind"])
            for v in ("r6", "cs", "stt"):
                chain_row(f"  voice {v}", [t for t in bl if t["voice"] == v], pred["blind"])
            if wrong:
                for t in bl:
                    if parse(pred["blind"][t["id"]]) != t["orders"]:
                        print(f"      {t['id']}  {t['text']!r}\n          truth {t['orders']}  answer {parse(pred['blind'][t['id']])}")
        print(f"  {'held-out single lines (no threshold)':52s} {'n':>5s} {'one intent':>11s} {'near':>6s} {'wrong fam':>10s} {'criterion':>10s}")
        for cond, label in (("typed", "typed"), ("vctkB", "heard from unseen voices")):
            single_row(f"this variant, {label}", cond, lambda k: parse(pred["singles"][k]))

    # the same single rows read by the models that only ever answer with one intent
    refs = []
    p = Q.path_of(NAME, "r16", 0)
    if os.path.exists(p):
        refs.append(("the decoder taught on single lines (qlora_v54.py)", json.load(io.open(p, encoding="utf-8"))["probs"]))
    tf = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2) if os.path.exists(os.path.join(HERE, f"kd54_teacher_s{s}.json"))]
    if tf:
        refs.append(("the classifier ensemble's fold teachers", {k: [sum(r["0"]["test"][k][j] for r in tf) / len(tf) for j in range(len(V.INTENTS))] for k in tf[0]["0"]["test"]}))
    if refs:
        print(f"\n  {'for comparison, on the same rows (no threshold)':52s} {'n':>5s} {'one intent':>11s} {'near':>6s} {'wrong fam':>10s} {'criterion':>10s}")
        for name, probs in refs:
            for cond, label in (("typed", "typed"), ("vctkB", "heard from unseen voices")):
                single_row(f"{name[:38]}, {label[:12]}", cond, lambda k: [V.pick(probs[k], "top", 0.0)[0]] if k in probs else [])

    # what today's bot does with a line that has several orders: it gives one intent or asks again
    p = os.path.join(CH, "blind_bot.json")
    if bl and os.path.exists(p):
        bot = json.load(io.open(p, encoding="utf-8"))
        multi = [t for t in bl if len(t["orders"]) > 1]
        first = sum(bot[t["id"]][0] == t["orders"][0] for t in multi)
        later = sum(bot[t["id"]][0] in t["orders"][1:] and bot[t["id"]][0] != t["orders"][0] for t in multi)
        asks = sum(bot[t["id"]][0] == "NONE" for t in multi)
        print(f"\ntoday's bot (the v54 ensemble, one intent per line) on the {len(multi)} blind lines with several orders: it does the first order "
              f"on {first}, a later one on {later}, something else on {len(multi) - first - later - asks}, asks again or does nothing on {asks}")
        ones = [t for t in bl if len(t["orders"]) == 1]
        print(f"  and on the {len(ones)} blind lines with one order it picks that order on {sum(bot[t['id']][0] == t['orders'][0] for t in ones)}")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "check":
        check()
    elif mode == "train":
        train(sys.argv[2], int(sys.argv[3]))
    elif mode == "answer":
        answer(sys.argv[2], int(sys.argv[3]))
    elif mode == "score":
        score("--wrong" in sys.argv)
    else:
        sys.exit(__doc__)
