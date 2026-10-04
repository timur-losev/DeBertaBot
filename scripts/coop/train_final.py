"""
Trains the model the co-op bot ships with, and saves it.

The study (train_bert.py, select_bert.py) kept only probabilities: every model was trained on two
authors and thrown away after scoring the third. A bot needs one model trained on everything:

  data       all 363 labelled lines (3 authors), label = the majority of author + 2 annotators
  recipe     microsoft/deberta-v3-base, fp32, lr 5e-5, batch 16, 20 epochs, AdamW wd 0.01,
             10% linear warm-up, max 64 tokens -- the fixed recipe; the nested search
             (select_bert.py) did not beat it measurably (+2.0 / +3.2 points, CIs span zero)
  threshold  5-fold out-of-fold predictions over the same 363 lines, each fold trained for the same
             number of optimizer steps as the final model; the threshold maximises
             near - 2 * wrong-family (strict: only NONE counts as doing nothing)
  output     ../../models/coop-deberta-v3-base/: weights (safetensors), tokenizer, bot_config.json

Reuses train_bert.train_predict / train_bert.oof and select_bert.criterion, so the shipped model is
made exactly the way the measured ones were.

    python train_final.py          # jev environment; uses the GPU if there is one, CPU otherwise
"""
import io, json, os, sys, time

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_coop as C  # noqa: E402
import select_bert as SB  # noqa: E402
import train_bert as T  # noqa: E402

NAME = "microsoft/deberta-v3-base"
SEED = 0
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "models", "coop-deberta-v3-base"))


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    items = C.load_test()
    # --seeds: add the developer's canonical short commands (seed_commands.json) to training. The first
    # live test showed the blind data has almost no plain phrasings ('come here', 'breach'); a
    # leave-one-author-out check (seed_check.py) showed seeds also help on lines far from any seed.
    seeds = []
    if "--seeds" in sys.argv:
        import seed_check
        seeds = seed_check.seed_items()
    t0 = time.time()

    oof = T.oof(NAME, items + seeds, SEED, device)              # 5 folds, matched steps
    # the threshold is fitted on the study lines only: the seed commands are too easy to calibrate on
    crit, threshold = SB.criterion({k: v for k, v in oof.items() if not k.startswith("seed_")}, items)
    print(f"out-of-fold: {len(oof)} lines ({len(seeds)} seeds), threshold {threshold:.2f} "
          f"(near - 2*wrong-family = {crit} of {len(items)}), {time.time()-t0:.0f}s", flush=True)

    _, model, tok = T.train_predict(NAME, items + seeds, items[:1], SEED, device)
    os.makedirs(OUT, exist_ok=True)
    model.to("cpu").save_pretrained(OUT, safe_serialization=True)
    tok.save_pretrained(OUT)
    cfg = {
        "labels": T.LABELS,
        "threshold": threshold,
        "families": C.FAMILY,
        "phrases": {k: v["label"] for k, v in C.I.items()},
        "base_model": NAME,
        "recipe": {**T.HP, "lr": T.HP["lr"]["base"], "dtype": "float32", "seed": SEED},
        "trained_on": f"{len(items)} lines from 3 AI-written authors (blind/author_*.json), "
                      "majority of author + 2 AI annotators"
                      + (f", plus {len(seeds)} developer-written canonical commands (seed_commands.json)"
                         if seeds else ""),
        "threshold_from": "5-fold out-of-fold predictions, criterion near - 2*wrong-family, strict",
        "expected_quality": "leave-one-author-out, same recipe, OOF threshold: near 75.5, wrong family "
                            "4.8, acts on non-order 13.7; on lines unlike the training set 66.0 near "
                            "(see COOP-BOT.md). Real player speech will be worse.",
    }
    json.dump(cfg, io.open(os.path.join(OUT, "bot_config.json"), "w", encoding="utf-8"), indent=1)
    print(f"saved to {OUT} in {time.time()-t0:.0f}s total", flush=True)


if __name__ == "__main__":
    main()
