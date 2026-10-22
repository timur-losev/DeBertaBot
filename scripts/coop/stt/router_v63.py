"""The router for chain v63 (2026-10-22): router v59's rows and recipe (router_v59.py, round "final"), with the English short
pairs of chains7_v63.py ("reload and cover me": two short orders joined by "and") as lines for the decoder, and without the
singles chains7_v63.py left out of the decoder's rows (a line whose halves around "and" read as two orders of different
families: the rows said "one order", the pairs say "two"). Router v59 sent "reload and cover me" to the classifier (0.00) and
"throw a grenade and push in" half way (0.49): the classifier then ran the first order only.

    python chains7_v63.py data ... (the pairs: chains2/ml_v62/pairs_train_en.json, the test: pairs_test.json)
    python router_v63.py train final small 0   -> models/coop-router-deberta-v3-small-v63 and router63_final_small_s0.json
    python router_v63.py probe                 router v59 and v63 on the pairs test, the left-out singles and the owner's lines
"""
import io, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import router_v59 as R          # first: chains5_v59 (COOP_TAG=v58) and the router's rows
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
from router_v59 import B, D, T

EPOCHS, CUT = R.EPOCHS, R.CUT
ML = os.path.join(HERE, "chains2", "ml_v62")
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
# the owner's English lines of the kind (and the English of their Russian ones), never trained on
OWNER = ["come here and jump", "jump and come to me", "jump up and shoot", "go up and come down to me", "reload and cover me",
         "throw a grenade and push in", "come here to me and jump", "jump and come here", "crouch and shoot"]


def pairs():
    return json.load(io.open(os.path.join(ML, "pairs_train_en.json"), encoding="utf-8"))


def left_out():
    return {B.norm(t) for t in json.load(io.open(os.path.join(ML, "singles_left_out_v63.json"), encoding="utf-8"))}


def rows_final():
    rows, tests = R.rows_final()
    out = left_out()
    kept = [r for r in rows if B.norm(r["text"]) not in out]
    added = [{"text": t, "route": True} for t in pairs()]
    return kept + added, tests, {"v59_rows": len(rows), "left_out": len(rows) - len(kept), "pairs": len(added)}


def extra_tests():
    test = json.load(io.open(os.path.join(ML, "pairs_test.json"), encoding="utf-8"))["en"]
    return {"pairs_en": [{"id": t["id"], "text": t["text"]} for t in test],
            "left_out": [{"id": f"lo{n}", "text": t} for n, t in enumerate(sorted(left_out()))],
            "owner": [{"id": f"own{n}", "text": t} for n, t in enumerate(OWNER)]}


def read(model, tok, tests):
    model.eval()
    probs = {}
    with torch.no_grad():
        for name, ts in tests.items():
            tb = T.batcher(tok, ts, D.DEVICE)
            out = {}
            for b in range(0, len(ts), 64):
                p = torch.softmax(model(**tb(list(range(b, min(b + 64, len(ts)))))).logits.float(), -1)[:, 1].cpu().tolist()
                out.update({t["id"]: round(v, 4) for t, v in zip(ts[b:b + 64], p)})
            probs[name] = out
    return probs


def train(size, seed):
    t0 = time.time()
    rows, tests, counts = rows_final()
    tests.update(extra_tests())
    random.seed(seed)
    torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(D.MODELS[size])
    model = AutoModelForSequenceClassification.from_pretrained(D.MODELS[size], num_labels=2, dtype=torch.float32).to(D.DEVICE)
    batch = T.batcher(tok, rows, D.DEVICE)
    y = torch.tensor([int(r["route"]) for r in rows], device=D.DEVICE)
    order = list(range(len(rows)))
    steps = EPOCHS * B.steps(len(rows))
    opt = torch.optim.AdamW(model.parameters(), lr=D.LR[size], weight_decay=T.HP["weight_decay"], fused=D.DEVICE == "cuda")
    sched = get_linear_schedule_with_warmup(opt, int(T.HP["warmup"] * steps), steps)
    model.train()
    for _ in range(EPOCHS):
        random.shuffle(order)
        for b in range(0, len(order), T.HP["batch"]):
            idx = order[b:b + T.HP["batch"]]
            loss = model(**batch(idx), labels=y[torch.tensor(idx, device=D.DEVICE)]).loss
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
    probs = read(model, tok, tests)
    json.dump({"round": "final", "size": size, "seed": seed, "rows": len(rows), "counts": counts, "several": int(y.sum()), "epochs": EPOCHS,
               "train_s": round(time.time() - t0), "probs": probs},
              io.open(os.path.join(HERE, f"router63{os.environ.get('ROUTER63_TAG', '')}_final_{size}_s{seed}.json"), "w", encoding="utf-8"))
    d = os.path.join(MODELS, f"coop-router-deberta-v3-{size}-v63{os.environ.get('ROUTER63_TAG', '')}" + (f"_s{seed}" if seed else ""))
    os.makedirs(d, exist_ok=True)
    model.to("cpu").save_pretrained(d, safe_serialization=True)
    tok.save_pretrained(d)
    json.dump({"rows": len(rows), "counts": counts, "for_the_decoder": int(y.sum()), "epochs": EPOCHS, "cut": CUT,
               "labels": ["ensemble", "decoder"], "base_model": D.MODELS[size], "seed": seed}, io.open(os.path.join(d, "router_config.json"), "w"), indent=1)
    print(f"router v63 {size} seed {seed}: {len(rows)} rows ({counts}), {int(y.sum())} of them for the decoder, {EPOCHS} epochs, {time.time() - t0:.0f}s", flush=True)


def probe():
    """Router v59 (its saved model) on the sets router v63 was scored on at training, side by side: the share sent to the
    decoder (>= CUT) per set, the owner's lines one by one."""
    tests = extra_tests()
    v63 = json.load(io.open(os.path.join(HERE, "router63_final_small_s0.json"), encoding="utf-8"))["probs"]
    v59 = json.load(io.open(os.path.join(HERE, "router59_final_small_s0.json"), encoding="utf-8"))["probs"]
    d = os.path.join(MODELS, "coop-router-deberta-v3-small-v59")
    tok = AutoTokenizer.from_pretrained(d)
    model = AutoModelForSequenceClassification.from_pretrained(d, dtype=torch.float32).to(D.DEVICE)
    extra = read(model, tok, tests)
    json.dump({"probs": extra}, io.open(os.path.join(HERE, "router59_v63sets.json"), "w", encoding="utf-8"))   # for chains7_v63.py score
    v59.update(extra)
    out = io.StringIO()
    print(f"{'share sent to the decoder (>= ' + str(CUT) + ')':44s}{'v59':>8s}{'v63':>8s}", file=out)
    for name in sorted(v63):
        if name in v59 and isinstance(v63[name], dict) and v63[name]:
            ids = list(v63[name])
            share = lambda pr: 100 * sum(pr[k] >= CUT for k in ids) / len(ids)  # noqa: E731
            print(f"{name + ' (' + str(len(ids)) + ')':44s}{share(v59[name]):8.1f}{share(v63[name]):8.1f}", file=out)
    print("\nthe owner's lines:", file=out)
    for t in tests["owner"]:
        print(f"  {t['text']:40s}{v59['owner'][t['id']]:8.2f}{v63['owner'][t['id']]:8.2f}", file=out)
    print(out.getvalue(), end="")
    io.open(os.path.join(HERE, "router63_probe.log"), "w", encoding="utf-8").write(out.getvalue())


if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[1] == "train" and sys.argv[2] == "final":
        train(sys.argv[3], int(sys.argv[4]))
    elif len(sys.argv) > 1 and sys.argv[1] == "probe":
        probe()
    else:
        sys.exit(__doc__)
