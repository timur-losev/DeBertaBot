"""
The bot as shipped before v2 (models/coop-deberta-v3-base, 22 intents, threshold 0.78) on the v2 test
lines and the probes: the "before" column. It was trained on every v1 line, so only the v2 lines
(which it never saw) and the probes are scored. Its 22 probabilities are placed into the v2 label
order with 0 for TAKE_COVER and OPEN.

    python v1_on_v2.py        # jev environment; CPU is enough
"""
import io, json, os, sys

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_v2 as V  # noqa: E402

MODEL = os.path.normpath(os.path.join(HERE, "..", "..", "models", "coop-deberta-v3-base"))


def main():
    cfg = json.load(io.open(os.path.join(MODEL, "bot_config.json"), encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL, dtype=torch.float32).eval()
    lines = [i for i in V.load_items() if i["version"] == "v2"] + V.probe_items()
    out = {}
    with torch.no_grad():
        for b in range(0, len(lines), 32):
            batch = lines[b:b + 32]
            x = tok([i["text"] for i in batch], truncation=True, max_length=64, padding=True, return_tensors="pt")
            for it, row in zip(batch, torch.softmax(model(**x).logits, -1).tolist()):
                p = dict(zip(cfg["labels"], row))
                out[it["id"]] = [p.get(k, 0.0) for k in V.INTENTS]
    json.dump({"threshold": cfg["threshold"], "probs": out},
              io.open(os.path.join(HERE, "results_v1_on_v2.json"), "w", encoding="utf-8"))
    print(f"{len(out)} lines, threshold {cfg['threshold']}")


if __name__ == "__main__":
    main()
