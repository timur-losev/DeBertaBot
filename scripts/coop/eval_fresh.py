"""
A trained bot on the Mac review's fresh author (review_v3/fresh_author.json: 80 lines, 60 that name a
place and 20 plain orders), next to the two bots the review archived (the shipped v2 and the
Mac-trained v3). The scoring is eval_v3_review.py section G's: each bot at its own gate and
threshold, against the author's own label.

What this is and is not (review_v3/README.md): ONE AI author who is also the only labeller, short
seed-like lines, partial blindness. The lines were written before seed set v31 and were not read
when it was made (v31 came from the review's probes and from the v3 blind lines), so for a v31 model
they are an outside check of direction, not a blind rate.

    python eval_fresh.py ../../models/coop-deberta-v3-ens3-v31      # jev environment; writes review_v3/fresh_probs_<tag>.json
    python eval_fresh.py                                            # the stored bots only (any python)
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COOP_TAG", "v31")
import coop_v2 as V  # noqa: E402
import locations as LOC  # noqa: E402

REVIEW = os.path.join(HERE, "review_v3")


def lines():
    A = json.load(io.open(os.path.join(REVIEW, "fresh_author.json"), encoding="utf-8"))
    return [dict(l, maj=l["intent"], accept={l["intent"]},
                 target=(l["target"]["object"], l["target"]["qualifier"], l["target"]["zone"])) for l in A["lines"]]


def run_bot(model_dir, sl):
    import shipped
    P = shipped.Predictor(model_dir)
    name = os.path.basename(os.path.normpath(model_dir))
    out = {"model": name, "labels": P.labels, "gate": P.cfg["gate"], "threshold": P.cfg["threshold"],
           "families": P.cfg["families"], "probs": {l["id"]: p for l, p in zip(sl, P([l["text"] for l in sl]))}}
    path = os.path.join(REVIEW, f"fresh_probs_{name.rsplit('-', 1)[-1]}.json")
    json.dump(out, io.open(path, "w", encoding="utf-8", newline="\n"))
    return path


def main():
    sl = lines()
    for d in sys.argv[1:]:
        print("wrote", os.path.basename(run_bot(d, sl)))
    place, plain = [l for l in sl if l["cat"] != "plain"], [l for l in sl if l["cat"] == "plain"]
    exact = {}
    for l in sl:      # the matcher, current rule set: does the planner also get the place
        t = LOC.find(l["text"])["target"]
        exact[l["id"]] = ((t["object"], t["qualifier"], t["zone"]) if t else (None, None, None)) == l["target"]
    print(f"fresh author: {len(place)} lines that name a place, {len(plain)} plain orders; matcher rule set "
          f"v{LOC.VOCAB['version']} exact on {sum(exact[l['id']] for l in place)}/{len(place)} place lines")
    files = sorted(f for f in os.listdir(REVIEW) if f.startswith("fresh_probs_") and f.endswith(".json"))
    preds = {}
    for f in files:
        R = json.load(io.open(os.path.join(REVIEW, f), encoding="utf-8"))
        assert R["labels"] == V.INTENTS and R["families"] == V.FAMILY, f
        p = preds[R["model"]] = {k: V.pick(row, R["gate"], R["threshold"])[0] for k, row in R["probs"].items()}
        print(f"  {R['model']} ({R['gate']} gate, {R['threshold']:.2f})")
        for label, part in (("place lines", place), ("plain orders", plain)):
            s = V.score(p, part)
            near = [l for l in part if p[l["id"]] in l["accept"] or V.FAMILY[p[l["id"]]] == V.FAMILY[l["maj"]]]
            print(f"    {label:<12} near {s['near_count']}/{len(part)}   exact ok {round(s['ok'] * len(part))}/{len(part)}   "
                  f"wrong family {s['cross_count']}/{len(part)}"
                  + (f"   near and exact place {sum(exact[l['id']] for l in near)}/{len(part)}" if part is place else ""))
        miss = [l for l in sl if not (p[l["id"]] in l["accept"] or V.FAMILY[p[l["id"]]] == V.FAMILY[l["maj"]])]
        print("    not near: " + ("; ".join(f"{l['id']} {l['intent']} -> {p[l['id']]}" for l in miss) or "none"))
    names = list(preds)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            good = lambda p, l: p[l["id"]] in l["accept"] or V.FAMILY[p[l["id"]]] == V.FAMILY[l["maj"]]   # noqa: E731
            up = sum(good(preds[names[b]], l) and not good(preds[names[a]], l) for l in sl)
            down = sum(good(preds[names[a]], l) and not good(preds[names[b]], l) for l in sl)
            print(f"  {names[b]} against {names[a]}, near: {up} lines better, {down} worse")


if __name__ == "__main__":
    main()
