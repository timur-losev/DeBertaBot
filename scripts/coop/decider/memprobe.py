"""Peak GPU memory and time of one LoRA training step (shared prefix with grad, a batch of suffixes), per batch size.
Stops before a size that would pass 20 GB, so Windows never spills video memory into system RAM.

    python memprobe.py 8 16 32
"""
import sys, time
import torch
import common as C

PREFIX_GRAD = "--prefix-grad" in sys.argv
sys.argv = [a for a in sys.argv if a != "--prefix-grad"]
tok = C.tokenizer()
pre, lab, suffix = C.prompt_parts(tok)
C.patch_cache_for_autograd()
lm = C.load_model()
from peft import LoraConfig, get_peft_model
pm = get_peft_model(lm, LoraConfig(r=16, lora_alpha=32, target_modules="all-linear", lora_dropout=0.0))
opt = torch.optim.AdamW([p for p in pm.parameters() if p.requires_grad], lr=1e-4)
lines = ["should this wall", "go up by the stairs and open fire", "kiss him", "follow me", "build a wall", "what should I do",
         "Mag's empty and there's no time, just swap to the pistol.", "get the seeds from the shed and bring em to me"]
base = torch.cuda.memory_allocated() / 2**30
print(f"model + LoRA + optimizer state: {base:.1f} GB")
for B in map(int, sys.argv[1:]):
    batch = [suffix(t) for t in (lines * 8)[:B]]
    gold = torch.zeros(B, dtype=torch.long, device=lm.device)
    ts = []
    for i in range(3):
        torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize(); t0 = time.time()
        loss = torch.nn.functional.cross_entropy(C.label_logits(lm, pre, batch, lab, prefix_grad=PREFIX_GRAD), gold)
        loss.backward(); opt.step(); opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize(); ts.append(time.time() - t0)
    peak = torch.cuda.max_memory_allocated() / 2**30
    print(f"batch {B:3}: peak {peak:.1f} GB, step {min(ts):.2f} s ({min(ts) / B * 1000:.0f} ms per line)")
    if peak * 2 > 20:
        print("next size would pass 20 GB: stop"); break
