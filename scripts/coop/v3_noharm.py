"""
Does rewriting the line for the classifier (locations.normalized) change what the v2 bot answers on
the lines it already handles? The 483 v1+v2 lines, two inputs: raw and "strip".

The v2 bot (models/coop-deberta-v3-ens3-v2) was trained on these lines, so this is not a quality
measurement -- only a check that the rewrite does not flip answers on known lines. Quality on lines
with map locations is eval_v3.py, on lines the model never saw. (The first run, before the rules were
frozen, also had a "strip+zone" mode that replaced floors; it changed the meaning of orders and was
dropped from locations.normalized.)

    python v3_noharm.py      # jev environment
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_v2 as V  # noqa: E402
import locations as LOC  # noqa: E402
import shipped  # noqa: E402


def main():
    items = V.load_items(with_v3=False)
    P = shipped.Predictor(os.path.normpath(os.path.join(HERE, "..", "..", "models", "coop-deberta-v3-ens3-v2")))
    gate, thr = P.cfg["gate"], P.cfg["threshold"]
    res = {}
    base = None
    for mode in ("raw", "strip"):
        texts = [LOC.normalized(i["text"], mode) for i in items]
        probs = P(texts)
        preds = {i["id"]: V.pick(p, gate, thr)[0] for i, p in zip(items, probs)}
        s = V.score(preds, items)
        changed_text = [i for i, t in zip(items, texts) if t != i["text"]]
        if base is None:
            base = preds
        flips = [(i["id"], i["text"], t, i["maj"], base[i["id"]], preds[i["id"]])
                 for i, t in zip(items, texts) if preds[i["id"]] != base[i["id"]]]
        res[mode] = {"near": s["near"], "cross": s["cross"], "ok": s["ok"], "changed_lines": len(changed_text),
                     "flips": flips}
        print(f"{mode:<11} lines rewritten {len(changed_text):>3}  near {100*s['near']:.1f}  wrong family "
              f"{100*s['cross']:.1f}  answers changed vs raw {len(flips)}")
        for f in flips:
            print(f"     {f[0]} {f[1]!r} -> {f[2]!r}: truth {f[3]}, raw {f[4]}, now {f[5]}")
    json.dump(res, io.open(os.path.join(HERE, "results_v3_noharm.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
