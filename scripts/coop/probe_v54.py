"""A typed probe of a bot: the lines of probe_v54.txt, each with the reading wanted for it, through the Python bot as the
chat would run them (the classifier reads the line lowercased and without its final .!?; the regex slots and the place
matcher read the line itself).

    text => WANT1/WANT2 [@pin | @this] [now | signal]

  WANT      the bot is right when it acts on one of these orders, or -- where NONE is wanted -- when it does nothing
            (ignores the line or asks again); for the four answers "acts" is the action "answer"
  @pin      the place record's primary target must point with the pin; @this: with this / that / here / there
  now       the line must not be queued for a go; signal: it must be

probe_v54.txt was written by the developer who wrote seed set v54 and rule set v5, before bot v54 was trained and before
any v54 result: wordings next to the new intents, the pin, and a few older orders. Not blind -- he wrote the seeds, some
lines are seeds and the wanted readings are his reading of spec v54 -- but it cannot have been tuned to the bot's answers.

    python probe_v54.py ../../models/coop-deberta-v3-ens3-v54 [FILE.txt]     # CPU
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_bot  # noqa: E402

norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()  # noqa: E731
model = sys.argv[1]
source = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "probe_v54.txt")
bot = coop_bot.Bot(model_dir=model)
name = os.path.basename(os.path.normpath(model))
seed_file = re.search(r"seed_commands_v[0-9]+\.json", json.load(io.open(os.path.join(model, "bot_config.json"), encoding="utf-8")).get("trained_on", ""))
seeds = io.open(os.path.join(HERE, seed_file.group(0)), encoding="utf-8").read() if seed_file else ""
rows = [l for l in io.open(source, encoding="utf-8").read().split("\n") if " => " in l]
right = wrong_act = n_seed = 0
print(f"{name}: gate {bot.gate}, threshold {bot.threshold}; {os.path.basename(source)}, {len(rows)} lines")
for row in rows:
    text, spec = row.split(" => ")
    parts = spec.split()
    want, flags = set(parts[0].split("/")), parts[1:]
    bot.reset()
    bot.classify(norm(text))
    _, rec = bot.decide(text, bot.last_probs)
    acts = rec["action"] in ("act", "queued", "execute", "go", "wait", "answer")
    ok = (acts and rec["intent"] in want) or (not acts and "NONE" in want)
    t = rec["places"]["targets"][rec["places"]["primary"]] if rec["places"]["targets"] else None
    ptr = t["pointer"] if t else None
    notes = []
    for f in flags:
        if f in ("@pin", "@this"):
            ok = ok and ptr == f[1:]
            notes.append(f"pointer {ptr or 'none'} (want {f[1:]})")
        elif f == "now":
            ok = ok and rec["action"] != "queued"
        elif f == "signal":
            ok = ok and rec["on_signal"]
    if rec["on_signal"]:
        notes.append("on signal")
    is_seed = '"' + text + '"' in seeds
    n_seed += is_seed
    right += ok
    wrong_act += acts and rec["intent"] not in want
    print(f"  {'ok ' if ok else 'NO '} {text!r:50} {rec['intent']:<16} {rec['prob']:.2f} {rec['action']:<9} want {spec:<32}"
          + ("  " + "; ".join(notes) if notes else "") + ("  [a seed]" if is_seed else ""))
print(f"{name}: {right}/{len(rows)} as wanted; acted on a wrong order: {wrong_act}; {n_seed} of the lines are its own seed commands")
