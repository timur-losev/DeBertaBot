"""decider-2b on the co-op bot's data: zero-shot, LoRA training, evaluation, merge (common.py has the prompt and the split).

    python run.py zeroshot [--seed 0 --fold 0]      the published model on the held-out lines -> results/zeroshot_s0f0.json
    python run.py train    [--seed 0 --fold 0]      LoRA on the fold's training rows -> OUT/lora_s0f0, then evaluates it
                                                     -> results/lora_s0f0.json
    python run.py merge    [--seed 0 --fold 0]      the LoRA folded into the weights, bf16 -> OUT/merged_s0f0 (for the GGUF)
    python run.py train --fold -1                   the game's model: LoRA on every row (lines, seeds, owner lines and
                                                     their transcripts, as build_v61.py's finals), no test -> OUT/lora_s0all;
                                                     then merge --fold -1 -> OUT/merged_s0all

Training: LoRA r 16, alpha 32, dropout 0.05 on every linear layer of the backbone (attention, delta-net, MLP), cross-entropy
over the 57 option-label logits at the slot (decider's own readout: the tied embedding rows of the label tokens), AdamW
lr 2e-4, 5% warm-up then cosine, 3 epochs, batches of 32 lines. The ~1,050-token prefix (question and options) runs once per
batch without gradient, with the current LoRA weights: the line's own tokens carry the gradient (memprobe.py: 13 GB and
18 ms per line at batch 32; with the prefix's gradient, 11 GB already at batch 4 and 284 ms per line).
A result file holds the raw label logits of every test row (key as in finaloof61_<seed>.json) and the timings.
"""
import argparse, io, json, math, os, random, time
import torch
import common as C

ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["zeroshot", "train", "merge"])
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--fold", type=int, default=0)
ap.add_argument("--epochs", type=int, default=3)
ap.add_argument("--batch", type=int, default=32)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--rank", type=int, default=16)
args = ap.parse_args()
tag = f"s{args.seed}all" if args.fold < 0 else f"s{args.seed}f{args.fold}"
os.makedirs(C.RES, exist_ok=True)
os.makedirs(C.OUT, exist_ok=True)
labels, _ = C.intents()
tok = C.tokenizer()
pre, lab, suffix = C.prompt_parts(tok)
C.patch_cache_for_autograd()


def evaluate(lm, test, name, extra):
    lm.eval()
    out, t0 = {}, time.time()
    rows = sorted(test, key=lambda r: len(suffix(r["text"])))          # similar lengths together: less padding
    with torch.no_grad():
        for i in range(0, len(rows), 64):
            chunk = rows[i:i + 64]
            lg = C.label_logits(lm, pre, [suffix(r["text"]) for r in chunk], lab, prefix_grad=False)
            for r, row in zip(chunk, lg.cpu().tolist()):
                out[r["id"]] = [round(x, 4) for x in row]
    dt = time.time() - t0
    acc = sum(labels[max(range(len(labels)), key=lambda j: out[r["id"]][j])] == r["maj"] for r in test) / len(test)
    path = os.path.join(C.RES, f"{name}_{tag}.json")
    json.dump({"model": name, "seed": args.seed, "fold": args.fold, "labels": labels, "n": len(test), "argmax_acc": acc,
               "eval_s": dt, **extra, "logits": out}, io.open(path, "w", encoding="utf-8"))
    print(f"{name}: {len(test)} test rows, argmax accuracy {100 * acc:.1f}%, {dt:.0f} s -> {path}", flush=True)


if args.mode == "merge":
    from peft import PeftModel
    lm = C.load_model(device="cpu")
    lm = PeftModel.from_pretrained(lm, os.path.join(C.OUT, f"lora_{tag}")).merge_and_unload()
    d = os.path.join(C.OUT, f"merged_{tag}")
    lm.save_pretrained(d, safe_serialization=True)
    tok.save_pretrained(d)
    print("merged ->", d)
    raise SystemExit

if args.fold < 0:
    train, test = C.everything(), []
else:
    train, test = C.split(args.seed, args.fold)
print(f"split seed {args.seed} fold {args.fold}: {len(train)} training rows, {len(test)} test rows; prefix {len(pre)} tokens", flush=True)
lm = C.load_model()
if args.mode == "zeroshot":
    evaluate(lm, test, "zeroshot", {"temperature_upstream": 1.18})
    raise SystemExit

from peft import LoraConfig, get_peft_model
torch.manual_seed(args.seed)
pm = get_peft_model(lm, LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, target_modules="all-linear"))
pm.print_trainable_parameters()
params = [p for p in pm.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
steps = args.epochs * math.ceil(len(train) / args.batch)
warm = max(1, int(0.05 * steps))
sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: (s + 1) / warm if s < warm else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, steps - warm))))
rng = random.Random(args.seed)
gold_of = {l: i for i, l in enumerate(labels)}
step, t0 = 0, time.time()
for ep in range(args.epochs):
    lm.train()
    order = list(train)
    rng.shuffle(order)
    run_loss = 0.0
    for i in range(0, len(order), args.batch):
        chunk = order[i:i + args.batch]
        logits = C.label_logits(lm, pre, [suffix(r["text"]) for r in chunk], lab, prefix_grad=False)
        loss = torch.nn.functional.cross_entropy(logits, torch.tensor([gold_of[r["maj"]] for r in chunk], device=lm.device))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
        step += 1
        run_loss += loss.item()
        if step % 50 == 0:
            print(f"epoch {ep} step {step}/{steps}: loss {run_loss / 50:.4f}, {time.time() - t0:.0f} s", flush=True)
            run_loss = 0.0
train_s = time.time() - t0
d = os.path.join(C.OUT, f"lora_{tag}")
pm.save_pretrained(d)
print(f"trained {steps} steps in {train_s:.0f} s -> {d}", flush=True)
if test:
    evaluate(lm, test, "lora", {"train_s": train_s, "epochs": args.epochs, "batch": args.batch, "lr": args.lr, "rank": args.rank,
                            "training_rows": len(train)})
