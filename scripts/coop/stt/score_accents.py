"""Speech-to-text output on the accented voices -> the v31 bot -> the project's criterion, per accent group.
Run in the jev environment. Reads out_<engine>_<vctk|kokoro|kokorox>.json and accents.json; read-only on the repository."""
import glob, io, json, os, re, sys
os.environ["COOP_TAG"] = "v31"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
os.chdir(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
import coop_v2 as V
import coop_bot as B

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(io.open(os.path.join(HERE, "lines.json"), encoding="utf-8"))
acc = json.load(io.open(os.path.join(HERE, "accents.json"), encoding="utf-8"))
items = {i["id"]: i for i in V.load_items()}
ref = {r["id"]: r["text"] for r in rows}
bot = B.Bot()
for m in bot.models:
    m.to("cuda")
cache = {}
lower = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()
words = lambda t: re.findall(r"[a-z0-9']+", t.lower())


def infer(texts):
    todo = [t for t in dict.fromkeys(texts) if t not in cache]
    for b in range(0, len(todo), 64):
        x = bot.tok(todo[b:b + 64], truncation=True, max_length=64, padding=True, return_tensors="pt").to("cuda")
        with torch.no_grad():
            p = torch.stack([torch.softmax(m(**x).logits.float(), -1) for m in bot.models]).mean(0).cpu().tolist()
        cache.update(zip(todo[b:b + 64], p))


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
    return 100 * err / max(n, 1)


def crit(hyp, ids):
    texts = {k: lower(hyp[k]) for k in ids}
    infer(texts.values())
    picks = {k: V.pick(cache[t], bot.gate, bot.threshold)[0] for k, t in texts.items()}
    s = V.score(picks, [items[k] for k in ids])
    return {"n": len(ids), "near": 100 * s["near"], "wf": 100 * s["cross"], "crit": 100 * (s["near"] - 2 * s["cross"]),
            "wer": wer([(ref[k], hyp[k]) for k in ids])}


out = {}
for cond in ("clean", "vctk", "kokoro", "kokorox"):
    files = sorted(glob.glob(os.path.join(HERE, f"out_*_{cond}.json")))
    if not files:
        continue
    groups = sorted({acc[k][cond]["group"] for k in ref}) if cond != "clean" else []
    print(f"\n=== {cond}: criterion (WER) per engine" + (f"; groups: {', '.join(groups)}" if groups else ""))
    for path in files:
        engine = os.path.basename(path)[4:-(len(cond) + 6)]
        hyp = {r["id"]: r["text"] for r in json.load(io.open(path, encoding="utf-8"))["rows"]}
        res = {"all": crit(hyp, list(hyp))}
        for g in groups:
            res[g] = crit(hyp, [k for k in hyp if acc[k][cond]["group"] == g])
        out.setdefault(cond, {})[engine] = res
        a = res["all"]
        print(f"{engine:20s} all: crit {a['crit']:5.1f} near {a['near']:5.1f} wf {a['wf']:4.1f}% WER {a['wer']:5.1f} | "
              + " | ".join(f"{g} {res[g]['crit']:.0f} ({res[g]['wer']:.0f})" for g in groups))
    if groups:
        print("   lines per group:", {g: sum(acc[k][cond]["group"] == g for k in ref) for g in groups})
json.dump(out, io.open(os.path.join(HERE, "score_accents.json"), "w", encoding="utf-8"), indent=1)
