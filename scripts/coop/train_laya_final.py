"""
The fine-tuned laya the bot would ship, and the question fine-tuning raises for laya specifically:
does it still work with a menu it was not fine-tuned on?

  1. final     fine-tune on all 363 study lines + the seed commands (seed 0, train_laya recipe);
               threshold from 5-fold out-of-fold predictions (fitted on the study lines only, as for
               DeBERTa); save to ../../models/coop-laya-ft/
  2. transfer  the squad-bot test set (../testset.json, 46 scored lines) with the squad bot's own
               16-option menu (../commands.json, labels + descriptions, chat.py's question) -- a menu
               the fine-tuning never saw. Zero-shot laya (this same PyTorch copy, parity-checked
               against ollaya) against the fine-tuned one.

    python train_laya_final.py
"""
import io, json, os, sys, time

import torch
from safetensors.torch import save_file

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import laya_torch as L  # noqa: E402
import run_coop as C  # noqa: E402
import select_bert as SB  # noqa: E402
import seed_check  # noqa: E402
import train_laya as TL  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "models", "coop-laya-ft"))
SQUAD = os.path.normpath(os.path.join(HERE, ".."))


def squad_eval(model):
    """Accuracy on the squad bot's 46 scored lines with its own 16-option menu (argmax)."""
    cmds = {k: v for k, v in json.load(io.open(os.path.join(SQUAD, "commands.json"), encoding="utf-8")).items()
            if not k.startswith("_")}
    crit = {v["label"]: v["description"] for v in cmds.values()}
    back = {v["label"]: k for k, v in cmds.items()}
    cases = json.load(io.open(os.path.join(SQUAD, "testset.json"), encoding="utf-8"))["cases"]
    instr = "Which order is the player giving the squad bot?"
    hit = n = 0
    model.eval()
    for c in cases:
        if c.get("want") is None:
            continue
        want = c["want"] if isinstance(c["want"], list) else [c["want"]]
        ids, mk, labels = L.Encoder.build(TL.E, f'Player said: "{c["text"]}"', instr, crit)
        with torch.no_grad():
            lg = model(*(t.to(TL.DEVICE) for t in TL.E.batch([(ids, mk, 0)])))[0, :len(labels)]
        n += 1
        hit += back[labels[int(lg.argmax())]] in want
    return hit, n


def main():
    items = C.load_test()
    seeds = seed_check.seed_items()
    t0 = time.time()

    base, _, _ = L.load_laya()
    base.to(TL.DEVICE)
    zh, zn = squad_eval(base)
    print(f"squad bot, zero-shot laya (PyTorch copy): {zh}/{zn}", flush=True)
    del base
    torch.cuda.empty_cache()

    o = TL.oof(items + seeds, 0)
    crit, thr = SB.criterion({k: v for k, v in o.items() if not k.startswith("seed_")}, items)
    print(f"out-of-fold threshold {thr:.2f} (near - 2*wf = {crit} of {len(items)}), {time.time()-t0:.0f}s", flush=True)

    # final model: same loop as train_predict, but keep the weights
    import random
    from transformers import get_linear_schedule_with_warmup
    random.seed(0)
    torch.manual_seed(0)
    model, _, _ = L.load_laya()
    model.to(TL.DEVICE).train()
    tr = [i for i in items + seeds if i["maj"]]
    steps = TL.EPOCHS * ((len(tr) + TL.BATCH - 1) // TL.BATCH)
    opt = torch.optim.AdamW(model.parameters(), lr=TL.LR, weight_decay=TL.WD)
    sched = get_linear_schedule_with_warmup(opt, int(TL.WARMUP * steps), steps)
    order = list(range(len(tr)))
    for _ in range(TL.EPOCHS):
        random.shuffle(order)
        for b in range(0, len(order), TL.BATCH):
            batch = [tr[j] for j in order[b:b + TL.BATCH]]
            rows, targets = [], []
            for it in batch:
                perm = list(range(len(TL.LABELS)))
                random.shuffle(perm)
                rows.append(TL.row(it["text"], perm))
                targets.append(perm.index(TL.IDX[it["maj"]]))
            ids, att, mp, mm, qt = (t.to(TL.DEVICE) for t in TL.E.batch(rows))
            loss = torch.nn.functional.cross_entropy(model(ids, att, mp, mm, qt), torch.tensor(targets, device=TL.DEVICE))
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
    fh, fn = squad_eval(model)
    print(f"squad bot, fine-tuned laya: {fh}/{fn}  (zero-shot {zh}/{zn})", flush=True)

    os.makedirs(OUT, exist_ok=True)
    save_file({k: v.detach().cpu().contiguous() for k, v in model.state_dict().items()},
              os.path.join(OUT, "model.safetensors"))
    json.dump({"labels": TL.LABELS, "intents": C.INTENTS, "threshold": thr, "families": C.FAMILY,
               "instructions": C.INSTR, "base": "laya:en (ollaya blob sha256-891102d3...)",
               "recipe": {"lr": TL.LR, "epochs": TL.EPOCHS, "batch": TL.BATCH, "wd": TL.WD,
                          "augment": "option order shuffled per example"},
               "trained_on": f"{len(items)} study lines + {len(seeds)} seed commands",
               "squad_transfer": {"zero_shot": [zh, zn], "fine_tuned": [fh, fn]}},
              io.open(os.path.join(OUT, "bot_config.json"), "w", encoding="utf-8"), indent=1)
    print(f"saved to {OUT}, {time.time()-t0:.0f}s total", flush=True)


if __name__ == "__main__":
    main()
