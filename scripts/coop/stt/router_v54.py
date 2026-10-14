"""One order or several? A small encoder in front of the chain decoder (chains_v54.py, chains2_v54.py).

The chain decoder reads a line with several orders, and pays for it on the lines with one: it splits 4% of the typed
single lines and 10% of those heard from unseen voices, so it cannot answer every line. The classifier ensemble reads
a single line better and cannot give a list at all. This is the switch between them: a DeBERTa-v3 with two classes,
trained on the very rows the chain decoder is trained on (a row is "several" when its answer has two orders or more),
on fold 0 of distill_v54.py's split. A line it calls "one" goes to the ensemble as today and never touches the GPU.

    python router_v54.py train ROUND SIZE SEED   ROUND: r1 (chains_v54.py's rows) | r2 | r3 (chains2_v54.py's rounds);
                                                 SIZE: xsmall | small | base -> router54_<ROUND>_<SIZE>_s<SEED>.json
                                                 (the probability of "several" for every test row)
    python router_v54.py score                   the tables, and the bot wired through each router
"""
import io, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
import chains_v54 as C
from chains_v54 import B, D, T, V

EPOCHS, CUT = 4, 0.5            # fixed before any result: a third of the classifier's epochs for a two-class question; the plain cut


def rounds(name):
    """(training rows, tests {name: [{"id", "text"}]}, the chain decoder's answers file) of a round. A row or a test line
    is for the decoder when its "route" says so, or, without one, when its "orders" are two or more."""
    if name == "r1":
        return C.training("teacher")[0], C.tests(), os.path.join(HERE, "chains54_teacher_s0.json")
    import chains2_v54 as C2
    if name == "r3":            # the round with more voices in the rows (chains2_v54.py: names3, pieces3)
        return C2.router_rows("names3"), C2.tests(), os.path.join(HERE, "chains2_54_names3_s0.json")
    if name == "final":         # round three's rows from EVERY line: the router for the game, its weights kept
        return C2.router_rows("names3_final"), C2.tests(), os.path.join(HERE, "chains2_54_names3_final_s0.json")
    return C2.router_rows(), C2.tests(), os.path.join(HERE, "chains2_54_names_s0.json")


def routed(r):
    return r["route"] if "route" in r else len(r["orders"]) > 1


def train(rnd, size, seed):
    t0 = time.time()
    rows, tests, _ = rounds(rnd)
    random.seed(seed)
    torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(D.MODELS[size])
    # fp32 explicitly, as train_v2.py: deberta-v3 checkpoints are saved in fp16
    model = AutoModelForSequenceClassification.from_pretrained(D.MODELS[size], num_labels=2, dtype=torch.float32).to(D.DEVICE)
    batch = T.batcher(tok, rows, D.DEVICE)
    y = torch.tensor([int(routed(r)) for r in rows], device=D.DEVICE)
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
    json.dump({"round": rnd, "size": size, "seed": seed, "rows": len(rows), "several": int(y.sum()), "epochs": EPOCHS, "train_s": round(time.time() - t0), "probs": probs},
              io.open(os.path.join(HERE, f"router54_{rnd}_{size}_s{seed}.json"), "w", encoding="utf-8"))
    if rnd == "final":
        d = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", f"coop-router-deberta-v3-{size}-v54"))
        os.makedirs(d, exist_ok=True)
        model.to("cpu").save_pretrained(d, safe_serialization=True)
        tok.save_pretrained(d)
        json.dump({"rows": len(rows), "for_the_decoder": int(y.sum()), "epochs": EPOCHS, "cut": CUT, "labels": ["ensemble", "decoder"], "base_model": D.MODELS[size], "seed": seed},
                  io.open(os.path.join(d, "router_config.json"), "w"), indent=1)
    print(f"router {rnd} {size} seed {seed}: {len(rows)} rows, {int(y.sum())} of them several, {EPOCHS} epochs, {time.time() - t0:.0f}s", flush=True)


def score():
    items = {i["id"]: i for i in B.LINES}
    tf = [json.load(io.open(os.path.join(HERE, f"kd54_teacher_s{s}.json"), encoding="utf-8")) for s in (0, 1, 2)]
    ens = {k: [sum(r["0"]["test"][k][j] for r in tf) / 3 for j in range(len(V.INTENTS))] for k in tf[0]["0"]["test"]}
    cfg = json.load(io.open(os.path.join(C.BOT, "bot_config.json"), encoding="utf-8"))
    for fn in sorted(f for f in os.listdir(HERE) if f.startswith("router54_") and f.endswith(".json")):
        r = json.load(io.open(os.path.join(HERE, fn), encoding="utf-8"))
        _, tests, chain_file = rounds(r["round"])
        pr = r["probs"]
        print(f"\nrouter {r['round']} {r['size']}, seed {r['seed']}: {r['rows']} rows ({r['several']} several), {r['train_s']} s; a line is sent to the chain decoder at {CUT}")
        print(f"  {'lines':58s} {'n':>5s} {'called several':>15s}")

        def sent(label, rows, name):
            if rows:
                print(f"  {label:58s} {len(rows):5d} {100 * sum(pr[name][t['id']] >= CUT for t in rows) / len(rows):14.1f}%")

        final = r["round"] == "final"       # trained on every line: fold 0's held-out lines are no test for it
        for cond, label in (("typed", "held-out single lines, typed"), ("vctkB", "held-out single lines, heard from unseen voices")):
            if not final:
                sent(label, [t for t in tests["singles"] if t["id"].split("|", 1)[0] == cond], "singles")
        for name in sorted(k for k in tests if tests[k] and "orders" in tests[k][0] and k in pr and not (final and k in ("joined", "unseen", "heard"))):
            rows = [t for t in tests[name] if t["orders"]]
            sent(f"{name}: for the ensemble (one order, stands by itself)", [t for t in rows if not routed(t)], name)
            sent(f"{name}: for the decoder (several orders, or leans on context)", [t for t in rows if routed(t)], name)
        if final or not os.path.exists(chain_file):
            continue
        # the bot wired through the router: the ensemble's pick, or the chain decoder's answer where the router says several
        pred = json.load(io.open(chain_file, encoding="utf-8"))["pred"]
        print(f"  {'held-out single lines through the router':58s} {'n':>5s} {'near':>6s} {'wrong fam':>10s} {'criterion':>10s}   (the ensemble alone)")
        for cond, label in (("typed", "typed"), ("vctkB", "heard from unseen voices")):
            ids = [t["id"] for t in tests["singles"] if t["id"].split("|", 1)[0] == cond]
            res = []
            for wired in (True, False):
                near = cross = 0
                for k in ids:
                    it = items[k.split("|", 1)[1]]
                    p = C.parse(pred["singles"][k]) if wired and pr["singles"][k] >= CUT else [V.pick(ens[k], cfg["gate"], cfg["threshold"])[0]]
                    good = len(p) == 1 and p[0] in V.FAMILY and (p[0] in it["accept"] or V.FAMILY[p[0]] == V.FAMILY[it["maj"]])
                    near += good
                    cross += not good and p != ["NONE"]
                res.append((100 * near / len(ids), 100 * cross / len(ids), 100 * (near - 2 * cross) / len(ids)))
            print(f"  {label:58s} {len(ids):5d} {res[0][0]:6.1f} {res[0][1]:9.1f}% {res[0][2]:10.1f}   ({res[1][0]:.1f}, {res[1][1]:.1f}%, {res[1][2]:.1f})")
        for name in sorted(k for k in tests if k.startswith("blind") and tests[k] and pred.get(name)):
            bot_file = os.path.join(os.path.dirname(chain_file), "chains" if r["round"] == "r1" else "chains2", f"{name}_bot.json")
            if not os.path.exists(bot_file):
                continue
            bot = json.load(io.open(bot_file, encoding="utf-8"))
            rows = [t for t in tests[name] if t["orders"]]
            print(f"  {name + ', exact list':58s} {'n':>5s} {'router':>7s} {'chain decoder alone':>20s} {'ensemble alone':>15s}")
            for label, sub in (("all", rows), ("one order", [t for t in rows if len(t["orders"]) == 1]), ("several orders", [t for t in rows if len(t["orders"]) > 1])):
                via = sum((C.parse(pred[name][t["id"]]) if pr[name][t["id"]] >= CUT else [bot[t["id"]][0]]) == t["orders"] for t in sub)
                dec = sum(C.parse(pred[name][t["id"]]) == t["orders"] for t in sub)
                one = sum([bot[t["id"]][0]] == t["orders"] for t in sub)
                print(f"    {label:56s} {len(sub):5d} {100 * via / len(sub):7.1f} {100 * dec / len(sub):20.1f} {100 * one / len(sub):15.1f}")


if __name__ == "__main__":
    if sys.argv[1] == "train":
        train(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif sys.argv[1] == "score":
        score()
    else:
        sys.exit(__doc__)
