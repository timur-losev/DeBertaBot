"""Smoke test of the saved bot: it loads through the project's own coop_bot.Bot and answers; next to bot v31.
classify()/decide() are used, which do not write coop_bot_log.jsonl."""
import os, sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
os.chdir(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
torch.set_num_threads(6)
import coop_bot as B
new = B.Bot(model_dir=sys.argv[1])
old = B.Bot(model_dir=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "models", "coop-deberta-v3-ens3-v31")))
print(f"new bot: gate {new.gate}, threshold {new.threshold}; v31: gate {old.gate}, threshold {old.threshold}")
tests = ["smoke the west window on my go", "diffuse it you've got time", "nate that room", "throw in the other room first",
         "north door is smoked", "split the angles. i take catch, you take the other one", "hold the north door",
         "reach the other hatch instead", "scrap the wrap hell call it off", "two on red stairs"]
for t in tests:
    row = []
    for bot in (old, new):
        bot.reset(); bot.classify(t)
        reply, rec = bot.decide(t, bot.last_probs)
        row.append(f"{rec['intent']} {rec['prob']:.2f} {rec['action']}")
    print(f"{t!r:58s} v31: {row[0]:32s} new: {row[1]}")
