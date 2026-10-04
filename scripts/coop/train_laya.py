"""
Fine-tunes laya:en (rebuilt in laya_torch.py, parity with ollaya checked) the way the DeBERTa bot was
fine-tuned, in laya's own input format -- the options stay in the input, so the menu can still change.

  input      state 'Player said: "<line>"', instructions run_coop.INSTR, criteria = the 22 phrase labels
             (the zero-shot winner for laya:en), question type choice
  loss       cross-entropy over the 22 option logits, target = the majority intent
  augment    the option order is shuffled for every training example, so the model cannot learn
             "option 9 is breach" and stays usable with other menus
  recipe     fixed in advance: lr 2e-5 (the head is already trained; a large step would wreck it),
             10 epochs, batch 16, AdamW wd 0.01, 10% warm-up, fp32
  protocol   leave one author out, 3 seeds; with --seeds the developer's seed commands join every
             training fold (never the test); with --oof also 5-fold out-of-fold predictions for the
             confidence threshold, trained for the same number of steps

Test probabilities are stored in results_bert_probs.json under "laya:en-ft" (or "laya:en-ft+seeds") in
run_coop.INTENTS order, so eval_bert.py and bootstrap_bert.py score them like the BERT classifiers.

    python train_laya.py [--seeds] [--oof] [--time-one]
"""
import io, json, os, random, sys, time

import torch
from transformers import get_linear_schedule_with_warmup

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import laya_torch as L  # noqa: E402
import run_coop as C  # noqa: E402

AUTHORS, SEEDS = ["r6", "cs", "stt"], [0, 1, 2]
LR, EPOCHS, BATCH, WD, WARMUP, K = 2e-5, 10, 16, 0.01, 0.1, 5
CRIT, _ = C.wording("phrase")              # {phrase label: None}, in C.INTENTS order
LABELS = list(CRIT)                        # phrase labels
IDX = {intent: i for i, intent in enumerate(C.INTENTS)}
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
E = L.Encoder()
PATH = os.path.join(HERE, "results_bert_probs.json")


def row(text, order):
    crit = {LABELS[j]: None for j in order}
    ids, mk, _ = E.build(f'Player said: "{text}"', C.INSTR, crit)
    return ids, mk, 0


def train_predict(train, tests, seed, epochs=EPOCHS):
    """-> {id: probs in C.INTENTS order} for every item in `tests` (softmax at T = 1)."""
    random.seed(seed)
    torch.manual_seed(seed)
    model, _, _ = L.load_laya()
    model.to(DEVICE).train()
    tr = [i for i in train if i["maj"]]
    steps = epochs * ((len(tr) + BATCH - 1) // BATCH)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    sched = get_linear_schedule_with_warmup(opt, int(WARMUP * steps), steps)
    order = list(range(len(tr)))
    for _ in range(epochs):
        random.shuffle(order)
        for b in range(0, len(order), BATCH):
            batch = [tr[j] for j in order[b:b + BATCH]]
            rows, targets = [], []
            for it in batch:
                perm = list(range(len(LABELS)))
                random.shuffle(perm)
                rows.append(row(it["text"], perm))
                targets.append(perm.index(IDX[it["maj"]]))
            ids, att, mp, mm, qt = (t.to(DEVICE) for t in E.batch(rows))
            logits = model(ids, att, mp, mm, qt)
            loss = torch.nn.functional.cross_entropy(logits, torch.tensor(targets, device=DEVICE))
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
    model.eval()
    out = {}
    fixed = list(range(len(LABELS)))
    with torch.no_grad():
        for b in range(0, len(tests), 32):
            chunk = tests[b:b + 32]
            ids, att, mp, mm, qt = (t.to(DEVICE) for t in E.batch([row(i["text"], fixed) for i in chunk]))
            p = torch.softmax(model(ids, att, mp, mm, qt)[:, :len(LABELS)], -1).cpu().tolist()
            out.update({i["id"]: r for i, r in zip(chunk, p)})
    del model
    torch.cuda.empty_cache()
    return out


def oof(train, seed):
    lines = [i for i in train if i["maj"]]
    random.Random(1000 + seed).shuffle(lines)
    full = EPOCHS * ((len(lines) + BATCH - 1) // BATCH)
    out = {}
    for f in range(K):
        te = lines[f::K]
        tr = [i for j, i in enumerate(lines) if j % K != f]
        ep = round(full / ((len(tr) + BATCH - 1) // BATCH))
        out.update(train_predict(tr, te, seed, epochs=ep))
    return out


def main():
    items = C.load_test()
    seeds = []
    if "--seeds" in sys.argv:
        import seed_check
        seeds = seed_check.seed_items()
    if "--time-one" in sys.argv:
        t0 = time.time()
        train = [i for i in items if i["author"] != "r6"]
        train_predict(train, [i for i in items if i["author"] == "r6"][:10], 0, epochs=1)
        print(f"one epoch over {len(train)} lines: {time.time()-t0:.0f}s on {DEVICE}")
        return
    key = "laya:en-ft" + ("+seeds" if seeds else "")
    res = json.load(io.open(PATH, encoding="utf-8"))
    store = res.setdefault(key, {})
    t0 = time.time()
    for held in AUTHORS:
        train = [i for i in items if i["author"] != held] + seeds
        test = [i for i in items if i["author"] == held]
        for s in SEEDS:
            k = f"{held}/{s}"
            if k in store and ("--oof" not in sys.argv or "oof" in store[k]):
                continue
            rec = store.get(k) or {"test": train_predict(train, test, s)}
            if "--oof" in sys.argv and "oof" not in rec:
                o = oof(train, s)
                rec["oof"] = {i: v for i, v in o.items() if not i.startswith("seed_")}
            store[k] = rec
            res = {**json.load(io.open(PATH, encoding="utf-8")), key: store}
            json.dump(res, io.open(PATH, "w", encoding="utf-8"))
            print(f"{key} held={held} seed={s} done, {time.time()-t0:.0f}s", flush=True)
    meta = json.load(io.open(PATH, encoding="utf-8"))
    meta.setdefault("_meta", {})[key] = {"lr": LR, "epochs": EPOCHS, "batch": BATCH, "wd": WD,
                                         "augment": "option order shuffled per example",
                                         "minutes": round((time.time() - t0) / 60, 1)}
    json.dump(meta, io.open(PATH, "w", encoding="utf-8"))


if __name__ == "__main__":
    main()
