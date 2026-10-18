"""The router for chain v58 over bot v57 (router_v55.py's recipe, round "final"): trained on round five's rows (chains4_v58.py:
the v57 lines and seeds, the v54 teacher lines, the context items of chains2/ctx_checked_v58.json, and the v58 items' lines as
heard). A context item leans on its talk when its pieces differ from its line: the new rules' lines (a pronoun for the last
order's thing, getting in and out of the car, going on with a movement, "another", a "no" and an order) now go to the decoder; a
repeat (with a place or not) and a negated order, written back as they are, do not. As round four, the "to this wall" seeds
(make_spec_v55.FRAGMENTS_TO) stay out of its rows for the ensemble.

    python router_v58.py train final small 0     -> models/coop-router-deberta-v3-small-v58 and router58_final_small_s0.json
"""
import io, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chains4_v58 as X        # first: COOP_TAG=v57, build_v57 in place of build_v54, the v57 calculator
X.C2.context_items = X.context_kept
import make_spec_v55
FRAGMENTS = {t for v in make_spec_v55.FRAGMENTS_TO.values() for t in v}
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
import chains_v54 as C
from chains_v54 import B, D, T, V

EPOCHS, CUT = 4, 0.5            # as round four: fixed before any result


def rows_final():
    """Round three's rows from EVERY line (names3_final) with round five's context items, the "to this wall" seeds out, and
    the v58 items' lines as heard."""
    C2 = X.C2
    rows = [r for r in C2.router_rows("names3_final") if r["route"] or r["text"].strip().lower() not in FRAGMENTS]
    new = [x for x in X.context_kept() if x["id"].startswith("x58_")]
    if os.path.exists(X.HEARD_V58):
        rows += [{"text": line, "route": C2.leans(x["line"], x["pieces"])} for x, _, line, _ in C2.context_heard(new, C2.VOICES["names3"], X.HEARD_V58)]
    return rows, C2.tests()


def train(size, seed):
    t0 = time.time()
    rows, tests = rows_final()
    random.seed(seed)
    torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(D.MODELS[size])
    # fp32 explicitly, as train_v2.py: deberta-v3 checkpoints are saved in fp16
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
    json.dump({"round": "final", "size": size, "seed": seed, "rows": len(rows), "several": int(y.sum()), "epochs": EPOCHS,
               "train_s": round(time.time() - t0), "probs": probs},
              io.open(os.path.join(HERE, f"router58_final_{size}_s{seed}.json"), "w", encoding="utf-8"))
    d = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", f"coop-router-deberta-v3-{size}-v58"))
    os.makedirs(d, exist_ok=True)
    model.to("cpu").save_pretrained(d, safe_serialization=True)
    tok.save_pretrained(d)
    json.dump({"rows": len(rows), "for_the_decoder": int(y.sum()), "epochs": EPOCHS, "cut": CUT, "labels": ["ensemble", "decoder"],
               "base_model": D.MODELS[size], "seed": seed}, io.open(os.path.join(d, "router_config.json"), "w"), indent=1)
    print(f"router final {size} seed {seed}: {len(rows)} rows, {int(y.sum())} of them for the decoder, {EPOCHS} epochs, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[1] == "train" and sys.argv[2] == "final":
        train(sys.argv[3], int(sys.argv[4]))
    else:
        sys.exit(__doc__)
