"""
Trained bots on the second batch of place lines (blind/v3b), which no model was trained on: the
probabilities of each bot directory for the raw lines. Probabilities only; eval_v3b.py scores them.

    python v3b_shipped.py                       # jev environment; the bots below that exist
    python v3b_shipped.py ../../models/coop-deberta-v3-ens3-v31      # one bot directory
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COOP_TAG", "v31")
import coop_v2 as V  # noqa: E402
import shipped  # noqa: E402

MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "models"))
BOTS = ["coop-deberta-v3-ens3-v2", "coop-deberta-v3-ens3-v3", "coop-deberta-v3-ens3-v31"]


def main():
    items = V.load_v3b()
    assert items, "no blind/v3b lines"
    dirs = [os.path.normpath(a) for a in sys.argv[1:]] or [os.path.join(MODELS, b) for b in BOTS]
    for d in dirs:
        if not os.path.exists(os.path.join(d, "bot_config.json")):
            print(f"skipped (not there): {d}")
            continue
        P = shipped.Predictor(d)
        out = {"model": os.path.basename(d), "threshold": P.cfg["threshold"], "gate": P.cfg["gate"],
               "trained_on": P.cfg.get("trained_on"),
               "probs": {i["id"]: p for i, p in zip(items, P([i["text"] for i in items]))}}
        path = os.path.join(HERE, f"results_v3b_{os.path.basename(d)}.json")
        json.dump(out, io.open(path, "w", encoding="utf-8"))
        print(f"{len(items)} v3b lines -> {os.path.basename(path)}")
        del P


if __name__ == "__main__":
    main()
