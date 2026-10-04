"""
The shipped bot (models/coop-deberta-v3-ens3-v2, trained before any line named a map place) on the
v3 lines, which it never saw: its probabilities for the raw line and for locations.normalized(line,
"strip"). Probabilities only; eval_v3.py scores them.

    COOP_TAG=v3 python v3_shipped.py      # jev environment
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COOP_TAG", "v3")
import coop_v2 as V  # noqa: E402
import locations as LOC  # noqa: E402
import shipped  # noqa: E402


def main():
    items = [i for i in V.load_items() if i["version"] == "v3"]
    P = shipped.Predictor()
    out = {"threshold": P.cfg["threshold"], "gate": P.cfg["gate"], "model": os.path.basename(shipped.MODEL_DIR)}
    for mode in ("raw", "strip"):
        texts = [LOC.normalized(i["text"], mode) for i in items]
        out[mode] = {i["id"]: p for i, p in zip(items, P(texts))}
        out[mode + "_text"] = {i["id"]: t for i, t in zip(items, texts)}
    json.dump(out, io.open(os.path.join(HERE, "results_v3_shipped.json"), "w", encoding="utf-8"))
    print(f"{len(items)} v3 lines, modes raw and strip ({sum(a != b for a, b in zip(out['raw_text'].values(), out['strip_text'].values()))} lines rewritten)")


if __name__ == "__main__":
    main()
