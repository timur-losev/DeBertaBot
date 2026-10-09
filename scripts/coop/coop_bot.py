"""
Talk to the co-op bot, on CPU: by default the v31 bot (bots.py: three fine-tuned DeBERTa-v3-base
models, train_v2.py final ens3 under COOP_TAG=v31; without its weights on this machine, the v2 bot);
--model ../../models/coop-deberta-v3-ens3-v2 for the bot trained without place lines,
../../models/coop-deberta-v3-base for the 22-intent v1 bot.

What happens to each line you type (the pipeline COOP-BOT.md recommends):
  1. regex slots   "on my go / when I say / on three" -> the order waits for your signal;
                   "other / another / opposite"       -> the planner takes the other object
  2. classifier    fine-tuned DeBERTa-v3 (one model, or several with their probabilities averaged:
                   bot_config.json "members"); softmax over its intents
  3. gate          the top intent's probability (gate "top"), or the mass of the top family and its
                   top intent (gate "family"); under the threshold -> "say again?" instead of acting
  1b. places       the map's named places in the line (locations.py): door / window / stairs with
                   their side or colour, furniture, floors; whose place each is; which one the bot acts on
  4. game side     NONE (a callout, chatter, a cancelled order) -> acknowledge, do nothing;
                   an order given "on my go" -> queued, with its places and its "other" slot;
                   GO_NOW -> executes the queued order;
                   HOLD_FIRE (a v5 bot) -> the bot stops shooting at once and keeps its queued order;
                   "hold fire until I say" queues OPEN_FIRE for the signal
Every line is appended to coop_bot_log.jsonl: in a real game those are the lines you label next.

    python coop_bot.py                   # jev environment; the fine-tuned DeBERTa
    python coop_bot.py --model DIR       # another trained bot (e.g. ../../models/coop-deberta-v3-base-v2)
    python coop_bot.py --laya            # the fine-tuned laya:en instead
    commands:  /why      toggle the debug line (top-3, slots, latency)
               /t 0.6    set the threshold (default: bot_config.json)
               /q        quit
"""
import io, json, os, random, sys, time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from timing_rule import ON_SIGNAL, OTHER  # noqa: E402  the two regexes measured in COOP-BOT.md
import bots  # noqa: E402
import locations as LOC  # noqa: E402  the map's named places in the line (COOP-BOT.md "v3")

import re  # noqa: E402

# the default bot: v31 (24 intents incl. TAKE_COVER and OPEN, trained with lines that name map places),
# three DeBERTa-v3-base seeds averaged, family gate (COOP-BOT.md "v3"); bots.py is the one place that names it
MODEL_DIR = bots.default_bot()
LAYA_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "models", "coop-laya-ft"))
# Safety net for polarity: the classifier reads the topic of a line, not whether it is negated
# ("do not come to me" -> FOLLOW_ME 0.93 in the first live test). Only a LEADING negation counts:
# a negator anywhere cost 22 points on the blind test's negator lines, because real orders carry one
# mid-sentence ("hold that door, don't let anyone through"); the leading form cost nothing there
# (seed_check.py). A bare "no" is left out: "no, the other door" is an order.
NEGATION = re.compile(r"^\W*(?:(?:uh|um|so|okay|ok|hey|bot|buddy|please|nah|no)\W+)*"
                      r"(don'?t|do not|dont|never|no need to)\b", re.I)
# HOLD_FIRE (v5 bots): "don't shoot" is an order to stop shooting, so its leading negation must not cancel it
SAFE = {"NONE", "WAIT", "HOLD_POSITION", "HOLD_FIRE"}
LOG = os.path.join(HERE, "coop_bot_log.jsonl")

LINES = {
    "FOLLOW_ME": ["On you.", "Right behind you.", "Moving with you."],
    "MOVE_TO": ["Moving to the ping.", "On my way there.", "Relocating."],
    "HOLD_POSITION": ["Holding here.", "Staying put.", "Not moving."],
    "HOLD_ANGLE": ["Holding that angle.", "Eyes on it.", "Angle locked."],
    "HOLD_OTHER_ANGLE": ["I've got the other side.", "Taking the other angle.", "Watching the other one."],
    "FLANK": ["Going around.", "Flanking, keep them busy.", "Taking the long way."],
    "VAULT_WINDOW": ["Going through the window.", "Vaulting in.", "Window, going."],
    "RAPPEL": ["On the rope.", "Rappelling.", "Heading up top."],
    "BREACH": ["Charge set, breaching!", "Blowing it open.", "Breaching!"],
    "DRONE": ["Droning it out.", "Drone's in.", "Scouting first."],
    "FLASH": ["Flash out!", "Popping a flash.", "Stun going in."],
    "SMOKE": ["Smoke out.", "Popping smoke.", "Smoking it."],
    "FRAG": ["Frag out!", "Nade going in.", "Throwing a frag."],
    "COVER_ME": ["Covering you, go.", "I've got your back.", "Go, I'm on it."],
    "ENTRY": ["Pushing in!", "Taking the room.", "Entry, entry!"],
    "FALL_BACK": ["Falling back.", "Pulling out.", "Backing off."],
    "PLANT": ["Planting.", "Getting the plant down.", "Plant going down, cover me."],
    "DEFUSE": ["Defusing.", "On the defuser.", "Working on it."],
    "REVIVE_ME": ["Coming to get you!", "Hold on, reviving.", "On my way, stay down."],
    "WAIT": ["Holding up.", "Standing by.", "Copy, waiting."],
    "TAKE_COVER": ["Getting into cover.", "Finding cover.", "Hiding."],
    "OPEN": ["Opening it.", "Getting it open.", "Opening, not going in."],
    "ATTACK": ["Attacking!", "Engaging.", "Going on the offensive."],
    "OPEN_FIRE": ["Opening fire!", "Weapons free.", "Firing!"],
    "HOLD_FIRE": ["Holding fire.", "Weapons tight.", "Ceasing fire."],
    "LOOK_AT": ["Looking.", "I see it.", "Turning to look."],
    "LOOK_AT_ME": ["Looking at you.", "Yeah, I see you.", "Facing you."],
    "HELP": ["Coming to help.", "On my way to you.", "Hang on, I'm coming."],
    "CHECK": ["Checking it.", "I'll check.", "Going to take a look."],
    "SUPPRESS": ["Suppressing!", "Covering fire!", "Keeping their heads down."],
    "JUMP": ["Jumping.", "On it, jumping.", "Going over."],
}
ACK = ["Copy.", "Noted.", "Heard."]                   # NONE: a callout or chatter, nothing to do
AGAIN = ["Say again?", "Didn't catch that.", "Come again?"]


class Bot:
    def __init__(self, laya=False, model_dir=MODEL_DIR):
        """laya=False: the fine-tuned DeBERTa classifier in model_dir (labels live in its weights).
        laya=True: the fine-tuned laya (models/coop-laya-ft): the 22 options are part of its input."""
        self.laya = laya
        self.gate = "top"
        if laya:
            import laya_torch as L
            from safetensors.torch import load_file
            d = LAYA_DIR
            cfg = json.load(io.open(os.path.join(d, "bot_config.json"), encoding="utf-8"))
            self.labels = cfg["intents"]
            self.phrase = dict(zip(cfg["intents"], cfg["labels"]))
            self.criteria = {p: None for p in cfg["labels"]}     # the menu, in intent order
            self.instructions = cfg["instructions"]
            self.enc = L.Encoder(os.path.join(d, "tokenizer.json"))
            self.model = L.Laya(d)
            self.model.load_state_dict(load_file(os.path.join(d, "model.safetensors")))
            self.model.eval()
        else:
            cfg = json.load(io.open(os.path.join(model_dir, "bot_config.json"), encoding="utf-8"))
            self.labels, self.phrase = cfg["labels"], cfg["phrases"]
            self.gate = cfg.get("gate", "top")
            # the C++ BotBrain refuses the same configs
            if self.gate not in ("top", "family"):
                raise ValueError(f"gate must be 'top' or 'family': {self.gate!r}")
            missing = [k for k in self.labels if k not in cfg["families"]]
            if missing:
                raise ValueError(f"no family for {missing}")
            dirs = [os.path.join(model_dir, m) for m in cfg.get("members", ["."])]
            self.tok = AutoTokenizer.from_pretrained(dirs[0])   # the members share the tokenizer
            self.models = [AutoModelForSequenceClassification.from_pretrained(d, dtype=torch.float32).eval()
                           for d in dirs]
        self.family = cfg["families"]
        self.threshold = cfg["threshold"]
        self.pending = None           # an order given "on my go", waiting for GO_NOW
        self.pending_places = None    # ... and the places that order named: they execute with it
        self.pending_other = False    # ... and its "other" slot: the GO line does not repeat it
        self.classify("warm up")      # the first call pays for allocation; do it before the player talks

    def classify(self, text):
        t0 = time.perf_counter()
        with torch.no_grad():
            if self.laya:
                ids, mk, _ = self.enc.build(f'Player said: "{text}"', self.instructions, self.criteria)
                logits = self.model(*self.enc.batch([(ids, mk, 0)]))[0, :len(self.labels)]
                p = torch.softmax(logits, -1).tolist()
            else:
                x = self.tok([text], truncation=True, max_length=64, return_tensors="pt")
                p = torch.stack([torch.softmax(m(**x).logits[0], -1) for m in self.models]).mean(0).tolist()
        top = sorted(range(len(p)), key=p.__getitem__, reverse=True)[:3]
        self.last_probs = p
        return [(self.labels[i], p[i]) for i in top], (time.perf_counter() - t0) * 1000

    def pick(self, p):
        """(intent, confidence) under the configured gate (coop_v2.pick)."""
        if self.gate == "top":
            j = max(range(len(p)), key=p.__getitem__)
            return self.labels[j], p[j]
        mass = {}
        for j, x in enumerate(p):
            mass[self.family[self.labels[j]]] = mass.get(self.family[self.labels[j]], 0.0) + x
        fam = max(mass, key=mass.get)
        j = max((j for j in range(len(p)) if self.family[self.labels[j]] == fam), key=p.__getitem__)
        return self.labels[j], mass[fam]

    def reset(self):
        """Forget the queued order (the C++ BotBrain::Reset)."""
        self.pending, self.pending_places, self.pending_other = None, None, False

    def respond(self, text):
        top, ms = self.classify(text)
        reply, rec = self.decide(text, self.last_probs)
        rec.update(t=time.strftime("%Y-%m-%dT%H:%M:%S"), top3=top, ms=round(ms, 1))
        with io.open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        return reply, rec

    def decide(self, text, p):
        """The game side for one line, given the classifier's probabilities (the C++ BotBrain::Decide)."""
        intent, prob = self.pick(p)
        places = LOC.record(text)     # for every line: under NONE they are contacts, not orders
        executed, executed_places, executed_other = None, None, False
        on_signal = bool(ON_SIGNAL.search(text))
        other = bool(OTHER.search(text))
        if NEGATION.search(text) and intent not in SAFE:
            self.reset()
            action, reply = "negated", "Copy, standing down."
        elif not prob >= self.threshold:      # also when the model returned NaN: never act on it
            action, reply = "say_again", random.choice(AGAIN)
        elif intent == "NONE":
            action, reply = "ignore", random.choice(ACK)
        elif intent == "GO_NOW":
            if self.pending:
                action, reply = "execute", f"Now! {random.choice(LINES[self.pending])}"
                # the queued order with its places and its "other" slot, not the GO line's
                executed, executed_places, executed_other = self.pending, self.pending_places, self.pending_other
                self.reset()
            else:
                action, reply = "go", "Going!"
        elif intent == "WAIT":
            self.reset()
            action, reply = "wait", random.choice(LINES["WAIT"])
        elif intent == "HOLD_FIRE":
            # stopping the shooting is never queued and does not cancel the queued order; "hold fire until I
            # say" is the one order whose signal means the opposite: the bot holds now and fires on the go
            action, reply = "act", random.choice(LINES["HOLD_FIRE"])
            if on_signal and "OPEN_FIRE" in self.labels:
                self.pending, self.pending_places, self.pending_other = "OPEN_FIRE", places, False
                reply += " On your go."
        elif on_signal:
            self.pending, self.pending_places, self.pending_other = intent, places, other
            action, reply = "queued", f"Ready to {self.phrase[intent]}. On your go."
        else:
            action, reply = "act", random.choice(LINES[intent])
        if other and action in ("act", "queued") and intent not in ("HOLD_OTHER_ANGLE", "HOLD_FIRE"):
            reply += " Taking the other one."
        rec = {"text": text, "intent": intent, "prob": prob, "gate": self.gate, "action": action,
               "on_signal": on_signal, "other": other, "threshold": self.threshold,
               "places": places, "executed": executed, "executed_places": executed_places,
               "executed_other": executed_other}
        return reply, rec


def main():
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    laya = "--laya" in sys.argv
    model_dir = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else MODEL_DIR
    print(f"loading the co-op bot ({'fine-tuned laya:en' if laya else os.path.basename(os.path.normpath(model_dir))}, "
          "CPU)...", flush=True)
    bot = Bot(laya=laya, model_dir=model_dir)
    why = True
    print(f"ready. threshold {bot.threshold:.2f}. Talk to your teammate in English; /why /t <x> /q\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text in ("/q", "/quit"):
            return
        if text == "/why":
            why = not why
            continue
        if text.startswith("/t "):
            bot.threshold = float(text.split()[1])
            print(f"  threshold {bot.threshold:.2f}")
            continue
        reply, rec = bot.respond(text)
        print(f"bot> {reply}")
        if why:
            (i1, p1), (i2, p2), (i3, p3) = rec["top3"]
            slots = [s for s, on in (("on my signal", rec["on_signal"]), ("other", rec["other"]),
                                     ("other (the queued order's)", rec["executed_other"])) if on]
            mass = f" | {bot.family[rec['intent']]} mass {rec['prob']:.2f}" if bot.gate == "family" else ""
            print(f"     {i1} ({bot.family[i1]}) {p1:.2f} | {i2} {p2:.2f} | {i3} {p3:.2f}{mass}"
                  f" | {rec['action']}" + (f" | slots: {', '.join(slots)}" if slots else "")
                  + (f" | queued: {bot.pending}" if bot.pending else "") + f" | {rec['ms']:.0f} ms")
            for label, pl in (("place", rec["places"]), ("executes at", rec["executed_places"])):
                if pl and pl["targets"]:
                    print(f"     {label}: " + "; ".join(
                        ("* " if k == pl["primary"] else "") + " ".join(
                            [str(t[f]) for f in ("qualifier", "object", "zone") if t[f]]
                            + ([f"dir={t['direction']}"] if t.get("direction") else []))
                        + "".join(f" [{t[f]}]" for f in ("role", "flag") if t[f]) for k, t in enumerate(pl["targets"])))


if __name__ == "__main__":
    main()
