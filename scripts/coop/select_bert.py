"""
A fair second look at ModernBERT: each model gets its own recipe and a hyperparameter search that
never sees the held-out author (nested cross-validation).

The first run (train_bert.py) used one fixed BERT/DeBERTa-style recipe for every model: 20 epochs,
no early stopping. ModernBERT ships with every dropout at 0.0 and its authors swept the learning
rate over {1e-5, 3e-5, 5e-5, 8e-5} with 1-10 epochs and early stopping, weight decay ~1e-5. So:

  outer   leave one author out, as everywhere in this study (242 training lines, 121 held out)
  inner   5 folds over the 242 training lines. For each learning rate, one 10-epoch run per fold;
          after every epoch the fold's held-out part is predicted, which gives out-of-fold (OOF)
          predictions for every (lr, epoch) pair from 4 runs x 5 folds. A pair is scored by the
          owner's criterion, near - 2 * wrong-family, at the best threshold on its own OOF
          predictions. The best pair wins; ties go to fewer epochs, then the lower rate.
  final   per seed (3), train on all 242 lines with the chosen rate, stopping at the chosen epoch of
          the same 10-epoch schedule, and predict the held-out author. The confidence threshold
          comes from the OOF predictions of the chosen pair for that seed.

Weight decay follows each family's published convention (ModernBERT 1e-5, DeBERTa-v3 0.01).
DeBERTa-v3-base goes through the same search, so the comparison is search against search.
Results go into results_bert_probs.json as "<model>@selected", which eval_bert.py picks up.

    python select_bert.py answerdotai/ModernBERT-base microsoft/deberta-v3-base answerdotai/ModernBERT-large
"""
import io, json, os, random, sys, time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_coop as C  # noqa: E402

LABELS = C.INTENTS
IDX = {k: i for i, k in enumerate(LABELS)}
AUTHORS = ["r6", "cs", "stt"]
SEEDS = [0, 1, 2]
LRS = [1e-5, 3e-5, 5e-5, 8e-5]
MAX_EPOCHS, BATCH, MAX_LEN, WARMUP, K = 10, 16, 64, 0.1, 5
WD = lambda name: 0.01 if "deberta" in name.lower() else 1e-5
PATH = os.path.join(HERE, "results_bert_probs.json")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_TOK = {}


def tok_for(name):
    if name not in _TOK:
        _TOK[name] = AutoTokenizer.from_pretrained(name)
    return _TOK[name]


def run(name, train, evals, seed, lr, stop_epoch=None):
    """Train with a MAX_EPOCHS linear schedule, stop after stop_epoch; after every epoch predict each
    set in `evals` ({tag: items}). Returns {epoch: {tag: {id: probs}}}."""
    stop_epoch = stop_epoch or MAX_EPOCHS  # read at call time: --max-epochs changes it after import
    random.seed(seed)
    torch.manual_seed(seed)
    tok = tok_for(name)
    model = AutoModelForSequenceClassification.from_pretrained(
        name, num_labels=len(LABELS), dtype=torch.float32).to(DEVICE)
    enc = lambda items: {k: v.to(DEVICE) for k, v in tok([i["text"] for i in items], truncation=True,
                                                         max_length=MAX_LEN, padding=True,
                                                         return_tensors="pt").items()}
    tr = [i for i in train if i["maj"]]
    per_epoch = (len(tr) + BATCH - 1) // BATCH
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WD(name))
    sched = get_linear_schedule_with_warmup(opt, int(WARMUP * MAX_EPOCHS * per_epoch), MAX_EPOCHS * per_epoch)
    order = list(range(len(tr)))
    out = {}
    for ep in range(1, stop_epoch + 1):
        model.train()
        random.shuffle(order)
        for b in range(0, len(order), BATCH):
            batch = [tr[j] for j in order[b:b + BATCH]]
            loss = model(**enc(batch), labels=torch.tensor([IDX[i["maj"]] for i in batch], device=DEVICE)).loss
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
        if ep == stop_epoch or evals.get("_every_epoch"):
            model.eval()
            res = {}
            with torch.no_grad():
                for tag, items in evals.items():
                    if tag.startswith("_"):
                        continue
                    probs = {}
                    for b in range(0, len(items), 64):
                        chunk = items[b:b + 64]
                        p = torch.softmax(model(**enc(chunk)).logits.float(), -1).cpu().tolist()
                        probs.update({i["id"]: row for i, row in zip(chunk, p)})
                    res[tag] = probs
            out[ep] = res
    del model
    torch.cuda.empty_cache()
    return out


def criterion(probs, items):
    """Best near_count - 2 * cross_count over thresholds, strict safety (only NONE is safe)."""
    C.SAFE = {"NONE"}
    raw = {}
    for k, row in probs.items():
        j = max(range(len(row)), key=row.__getitem__)
        raw[k] = (LABELS[j], row[j])
    sub = [i for i in items if i["id"] in raw]
    best = None
    for t in range(0, 100, 2):
        s = C.score(C.gate(raw, t / 100), sub)
        v = round(s["near"] * len(sub)) - 2 * round(s["cross"] * len(sub))
        if best is None or v > best[0]:
            best = (v, t / 100)
    C.SAFE = {"NONE", "WAIT", "HOLD_POSITION"}
    return best


def folds(lines, seed):
    lines = list(lines)
    random.Random(1000 + seed).shuffle(lines)
    return [(lines[f::K], [i for j, i in enumerate(lines) if j % K != f]) for f in range(K)]


def main():
    global LRS, MAX_EPOCHS
    args = sys.argv[1:]
    tag = ""
    if "--max-epochs" in args:
        # longer schedule: DeBERTa's first fold chose the 10-epoch cap itself
        MAX_EPOCHS = int(args[args.index("--max-epochs") + 1])
        tag = "-hi"
        args = [a for i, a in enumerate(args) if a != "--max-epochs" and (i == 0 or args[i - 1] != "--max-epochs")]
    if "--lrs" in args:
        # a wider grid, still searched only inside the training authors; stored under its own key
        LRS = [float(x) for x in args[args.index("--lrs") + 1].split(",")]
        tag = "-hi"
        args = [a for i, a in enumerate(args) if a != "--lrs" and (i == 0 or args[i - 1] != "--lrs")]
    names = [a for a in args if not a.startswith("--")]
    items = C.load_test()
    res = json.load(io.open(PATH, encoding="utf-8"))
    for name in names:
        key = f"{name}@selected{tag}"
        store = res.setdefault(key, {})
        t0 = time.time()
        for held in AUTHORS:
            train = [i for i in items if i["author"] != held and i["maj"]]
            test = [i for i in items if i["author"] == held]
            sel_key = f"_selection/{held}"
            if sel_key not in store:
                # inner search, seed 0: OOF predictions for every (lr, epoch)
                oof = {lr: {ep: {} for ep in range(1, MAX_EPOCHS + 1)} for lr in LRS}
                for val, tr in folds(train, 0):
                    for lr in LRS:
                        per_ep = run(name, tr, {"val": val, "_every_epoch": True}, 0, lr)
                        for ep, r in per_ep.items():
                            oof[lr][ep].update(r["val"])
                scores = {f"{lr}/{ep}": criterion(oof[lr][ep], train)[0] for lr in LRS for ep in oof[lr]}
                best = max(scores, key=lambda s: (scores[s], -int(s.split("/")[1]), -float(s.split("/")[0])))
                lr, ep = float(best.split("/")[0]), int(best.split("/")[1])
                store[sel_key] = {"lr": lr, "epoch": ep, "scores": scores,
                                  "oof_seed0": oof[lr][ep]}
                json.dump(res, io.open(PATH, "w", encoding="utf-8"))
                print(f"{key} held={held}: chose lr={lr} epoch={ep} "
                      f"(criterion {scores[best]} on {len(train)} OOF lines), {time.time()-t0:.0f}s", flush=True)
            sel = store[sel_key]
            for seed in SEEDS:
                k = f"{held}/{seed}"
                if k in store:
                    continue
                final = run(name, train, {"test": test}, seed, sel["lr"], sel["epoch"])[sel["epoch"]]["test"]
                if seed == 0:
                    oof_s = sel["oof_seed0"]
                else:
                    oof_s = {}
                    for val, tr in folds(train, seed):
                        oof_s.update(run(name, tr, {"val": val}, seed, sel["lr"], sel["epoch"])[sel["epoch"]]["val"])
                store[k] = {"test": final, "oof": oof_s}
                json.dump(res, io.open(PATH, "w", encoding="utf-8"))
                print(f"{key} held={held} seed={seed} done, {time.time()-t0:.0f}s", flush=True)
        res.setdefault("_meta", {})[key] = {"device": DEVICE, "lrs": LRS, "max_epochs": MAX_EPOCHS,
                                            "weight_decay": WD(name), "batch": BATCH, "inner_folds": K,
                                            "minutes": round((time.time() - t0) / 60, 1)}
        json.dump(res, io.open(PATH, "w", encoding="utf-8"))
        print(f"{key}: total {(time.time()-t0)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
