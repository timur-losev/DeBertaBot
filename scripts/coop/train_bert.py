"""
The classic approach the decision models are an alternative to: a BERT-family encoder fine-tuned as
a fixed-label classifier (22 intents in the output layer), on the studio's own labelled lines.

Same protocol as crossval.py / robustness.py: leave one author out. For each held-out author:
  full    train on the other two authors (242 lines), predict the held-out author (121)
  inner   train on one training author, predict the other, both ways -- the only data the
          confidence threshold is fitted on (in eval_bert.py), so nothing is tuned on the test lines
Hyperparameters are fixed in advance (below), not searched. Each run is repeated over 3 seeds,
because 242 examples for 22 classes is a small, noisy training set.

Writes class probabilities only; scoring is eval_bert.py (it needs scikit-learn, this needs torch).

    # in the jev environment (torch + transformers)
    python train_bert.py answerdotai/ModernBERT-base microsoft/deberta-v3-base [--cpu]
"""
import io, json, os, random, sys, time

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_coop as C  # noqa: E402  (stdlib only: the data and the label set)

LABELS = C.INTENTS
IDX = {k: i for i, k in enumerate(LABELS)}
AUTHORS = ["r6", "cs", "stt"]
SEEDS = [0, 1, 2]
HP = {"max_len": 64, "batch": 16, "epochs": 20, "weight_decay": 0.01, "warmup": 0.1,
      "lr": {"base": 5e-5, "large": 2e-5}}


def train_predict(name, train, test, seed, device, epochs=None):
    random.seed(seed)
    torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(name)
    # fp32 explicitly: transformers 5 loads a checkpoint in the dtype it was saved in, and
    # microsoft/deberta-v3-base is saved in fp16, where AdamW's eps (1e-8) rounds to zero and the
    # first step turns the weights into NaN. The ModernBERT checkpoints are fp32 either way.
    model = AutoModelForSequenceClassification.from_pretrained(
        name, num_labels=len(LABELS), dtype=torch.float32).to(device)
    size = "large" if "large" in name else "base"
    enc = lambda items: tok([i["text"] for i in items], truncation=True, max_length=HP["max_len"],
                            padding=True, return_tensors="pt")
    tr = [i for i in train if i["maj"]]
    order = list(range(len(tr)))
    epochs = epochs or HP["epochs"]
    steps = epochs * ((len(tr) + HP["batch"] - 1) // HP["batch"])
    opt = torch.optim.AdamW(model.parameters(), lr=HP["lr"][size], weight_decay=HP["weight_decay"])
    sched = get_linear_schedule_with_warmup(opt, int(HP["warmup"] * steps), steps)
    model.train()
    for _ in range(epochs):
        random.shuffle(order)
        for b in range(0, len(order), HP["batch"]):
            batch = [tr[j] for j in order[b:b + HP["batch"]]]
            x = {k: v.to(device) for k, v in enc(batch).items()}
            y = torch.tensor([IDX[i["maj"]] for i in batch], device=device)
            loss = model(**x, labels=y).loss
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
    model.eval()
    out = {}
    with torch.no_grad():
        for b in range(0, len(test), 64):
            batch = test[b:b + 64]
            x = {k: v.to(device) for k, v in enc(batch).items()}
            p = torch.softmax(model(**x).logits.float(), -1).cpu().tolist()
            out.update({i["id"]: row for i, row in zip(batch, p)})
    return out, model, tok


def oof(name, train, seed, device, k=5):
    """Out-of-fold predictions on the training authors, for fitting the confidence threshold.

    The first protocol fitted it on 'inner' models trained on one author (121 lines, 160 steps):
    they came out far less confident than the deployed model (DeBERTa median pmax 0.38 vs 0.85),
    so the threshold landed too low. Here each fold trains on ~4/5 of the same 242 training lines
    for the same number of optimizer steps as the deployed model (320), so its confidence scale
    matches. The held-out author is never touched."""
    lines = [i for i in train if i["maj"]]
    random.Random(1000 + seed).shuffle(lines)
    full_steps = HP["epochs"] * ((len(lines) + HP["batch"] - 1) // HP["batch"])
    out = {}
    for f in range(k):
        te = lines[f::k]
        tr = [i for j, i in enumerate(lines) if j % k != f]
        ep = round(full_steps / ((len(tr) + HP["batch"] - 1) // HP["batch"]))
        out.update(train_predict(name, tr, te, seed, device, epochs=ep)[0])
    return out


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--oof" in sys.argv:
        device = "cpu" if "--cpu" in sys.argv or not torch.cuda.is_available() else "cuda"
        items = C.load_test()
        path = os.path.join(HERE, "results_bert_probs.json")
        res = json.load(io.open(path, encoding="utf-8"))
        for name in names:
            t0 = time.time()
            for held in AUTHORS:
                train = [i for i in items if i["author"] != held]
                for seed in SEEDS:
                    run = res[name][f"{held}/{seed}"]
                    if "oof" in run:
                        continue
                    run["oof"] = oof(name, train, seed, device)
                    json.dump(res, io.open(path, "w", encoding="utf-8"))
                    print(f"{name} oof held={held} seed={seed} done, {time.time()-t0:.0f}s", flush=True)
        return
    device = "cpu" if "--cpu" in sys.argv or not torch.cuda.is_available() else "cuda"
    items = C.load_test()
    path = os.path.join(HERE, "results_bert_probs.json")
    try:
        res = json.load(io.open(path, encoding="utf-8"))
    except Exception:
        res = {}
    for name in names:
        t0 = time.time()
        for held in AUTHORS:
            train = [i for i in items if i["author"] != held]
            test = [i for i in items if i["author"] == held]
            a, b = [x for x in AUTHORS if x != held]
            A = [i for i in items if i["author"] == a]
            B = [i for i in items if i["author"] == b]
            for seed in SEEDS:
                key = f"{held}/{seed}"
                if key in res.get(name, {}):
                    continue
                full, model, tok = train_predict(name, train, test, seed, device)
                inner = {}
                inner.update(train_predict(name, A, B, seed, device)[0])
                inner.update(train_predict(name, B, A, seed, device)[0])
                res.setdefault(name, {})[key] = {"test": full, "inner": inner}
                json.dump(res, io.open(path, "w", encoding="utf-8"))
                print(f"{name} held={held} seed={seed} done, {time.time()-t0:.0f}s elapsed", flush=True)
        # CPU latency of the last trained model, one line at a time
        model = model.to("cpu").eval()
        ms = []
        with torch.no_grad():
            for i in items[:60]:
                x = tok([i["text"]], truncation=True, max_length=HP["max_len"], return_tensors="pt")
                t1 = time.perf_counter()
                model(**x)
                ms.append((time.perf_counter() - t1) * 1000)
        ms.sort()
        res.setdefault("_latency_cpu_ms", {})[name] = {"median": ms[len(ms) // 2], "p90": ms[int(.9 * len(ms))]}
        res.setdefault("_meta", {})[name] = {"device": device, "hp": HP, "seeds": SEEDS,
                                             "train_minutes": round((time.time() - t0) / 60, 1)}
        json.dump(res, io.open(path, "w", encoding="utf-8"))
        print(f"{name}: CPU latency median {ms[len(ms)//2]:.1f} ms, total {(time.time()-t0)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
