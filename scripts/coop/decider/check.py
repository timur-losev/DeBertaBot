"""Checks before the research runs: (1) the cached prefix gives the same slot logits as whole rows; (2) with a LoRA, the
gradient through the shared prefix equals the gradient of whole rows; (3) the time of one training step.

    python check.py
"""
import time
import torch
import common as C

torch.manual_seed(0)
tok = C.tokenizer()
pre, lab, suffix = C.prompt_parts(tok)
labels, options = C.intents()
print(f"prefix {len(pre)} tokens, {len(lab)} label tokens; suffix of 'should this wall': {len(suffix('should this wall'))} tokens")
print(repr(tok.decode(pre[:60])), "...", repr(tok.decode(pre[-30:])), "|", repr(tok.decode(suffix("should this wall"))))
C.patch_cache_for_autograd()
lm = C.load_model()
lines = ["should this wall", "go up by the stairs and open fire", "kiss him", "follow me", "build a wall", "what should I do"]
sufs = [suffix(t) for t in lines]
with torch.no_grad():
    a = C.label_logits(lm, pre, sufs, lab)
    b = C.full_label_logits(lm, pre, sufs, lab)
print("cached vs whole rows: max |d logit|", (a - b).abs().max().item(), "| argmax equal", (a.argmax(1) == b.argmax(1)).tolist())
for t, row in zip(lines, a):
    p = row.softmax(-1)
    print(f"  zero-shot {t!r:38} -> {labels[int(p.argmax())]:14} {p.max().item():.2f}")

from peft import LoraConfig, get_peft_model
pm = get_peft_model(lm, LoraConfig(r=8, lora_alpha=16, target_modules="all-linear", lora_dropout=0.0))
for n, p in pm.named_parameters():                      # make B non-zero so the LoRA changes something
    if "lora_B" in n:
        torch.nn.init.normal_(p, std=0.01)
gold = torch.tensor([labels.index(x) for x in ["OPEN_FIRE", "MOVE_TO", "ATTACK", "FOLLOW_ME", "BUILD", "NONE"]], device=lm.device)
probe = [p for n, p in pm.named_parameters() if p.requires_grad][:: 97][:6]
grads = []
for fn in (C.label_logits, C.full_label_logits):
    pm.zero_grad()
    loss = torch.nn.functional.cross_entropy(fn(lm, pre, sufs, lab), gold)
    loss.backward()
    grads.append([p.grad.detach().clone() for p in probe])
    print(f"{fn.__name__}: loss {loss.item():.5f}")
for g1, g2 in zip(*grads):
    print(f"  grad rel diff {((g1 - g2).norm() / (g2.norm() + 1e-12)).item():.2e}")

# one training step at the planned batch size
B = 32
batch = [suffix(t) for t in (lines * 6)[:B]]
gold_b = gold.repeat(6)[:B]
opt = torch.optim.AdamW([p for p in pm.parameters() if p.requires_grad], lr=1e-4)
for i in range(4):
    torch.cuda.synchronize(); t0 = time.time()
    loss = torch.nn.functional.cross_entropy(C.label_logits(lm, pre, batch, lab), gold_b)
    loss.backward(); opt.step(); opt.zero_grad()
    torch.cuda.synchronize()
    print(f"step {i}: {time.time() - t0:.2f} s, peak memory {torch.cuda.max_memory_allocated() / 2**30:.1f} GB")
