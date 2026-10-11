"""
Test data for the C++ planner (world.h), produced by scripts/coop/world.py: world_tests.jsonl next to the bot's
intent_config.json.

  Each row is one scenario: a world state (random entities with the vocabulary's objects, qualifiers and zones, a
  pin, a gaze, the bot's stance and items), the gate and the threshold, and a conversation of lines with constructed
  probabilities (no model). Per line what the Python planner did: the action ("ask" / "resolved" or the bot's), what
  it said on "ask" / "resolved", the grounding of every target, the order the game gets, the question still pending,
  the bot's queued order and its entity, the last entity remembered, the bot's pin. The lines are orders with places
  of every kind the rules know (a qualifier, a direction, a pointer, "the other", "the back door", a zone, a pin,
  "there"), given now or "on my go"; the answers (a bot with YES / NO / MAYBE / DONT_KNOW) and the places that settle a
  question ("the left one"); postures, "revive me", "plant", "defuse" (the priors); "go", "wait", a negation.
  Three scenarios in ten play in a world without named places (a map nobody has marked): untyped things, a pin, a
  gaze. There "here" is where the speaker is, "that door" is what the crosshair is on, a floor cannot be found, and
  the bot's "Where?" is answered by pointing ("there", "at my pin", "on the left") or by "yes" / "go" once the place
  is there.
  The short context: four scenarios in five carry the game's clock, and before every line the world moves on (time
  passes by half a second to a minute and a half, the bot is still busy or not, the pin is put, moved or taken away,
  the crosshair moves, sometimes onto an enemy). The lines include orders that name no place ("shoot", "move up",
  "check it"), repeats ("again", "shoot again", "once more"), corrections ("no", "no, here, on my pin"), fragments
  ("on my pin", "over there", "left") and lines whose words were lost ("should there"), with the confidence on
  either side of the threshold and of the "read it for its place alone" bound. Each step records the frame of the
  previous order. The owner's lines of the first live test (world.DEV_TALK) are the third scenario.
  The threshold is kept away from the adjusted confidence by 0.02 so that float32 cannot flip a step.
  A last block of worlds the rules must refuse (unknown object, duplicate id, bearing out of range, unknown stance).

    python gen_world_tests.py [BOT_DIR]      # jev environment; default: the shipped bot (scripts/coop/bots.py)
"""
import collections, io, json, os, random, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts", "coop"))
sys.path.insert(0, COOP)
os.environ.setdefault("COOP_TAG", "v54")
import bots  # noqa: E402
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
MODEL = os.path.normpath(_ARGS[0] if _ARGS else bots.default_bot())
OUT = os.path.join(MODEL, "cpp")
import coop_bot  # noqa: E402
import locations as LOC  # noqa: E402
import world as W  # noqa: E402

CFG = json.load(io.open(os.path.join(OUT, "intent_config.json"), encoding="utf-8"))
VOC = CFG["locations"]
assert any(k.startswith("pin_") for k in VOC["words"]), "the planner tests need a rule set v5 vocabulary (export_cpp.py --config-only)"
OBJECTS = {o["id"]: o["qualifiers"] for o in VOC["objects"]}
ZONES = [z["id"] for z in VOC["zones"]]
TAGS = ["closed", "cover", "bomb", "enemy", "rope"]


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


class Fake:
    """coop_bot.Bot.decide on the bot's own config, no model."""
    def __init__(self, gate, threshold):
        self.labels, self.phrase, self.family = CFG["labels"], CFG["phrases"], CFG["families"]
        self.gate, self.threshold = gate, threshold
        self.reset()
    reset = coop_bot.Bot.reset
    pick = coop_bot.Bot.pick
    decide = coop_bot.Bot.decide


ANSWER_LABELS = [a for a in coop_bot.ANSWERS if a in CFG["labels"]]
ORDERS = [k for k in CFG["labels"] if k not in ("NONE", "GO_NOW", "WAIT") and k not in ANSWER_LABELS]
PLACE_ORDERS = [k for k in ("HOLD_ANGLE", "MOVE_TO", "CHECK", "BREACH", "SMOKE", "HOLD_POSITION", "LOOK_AT", "OPEN", "FLASH", "FRAG",
                            "ENTRY", "VAULT_WINDOW", "TAKE_COVER", "SUPPRESS", "JUMP") if k in CFG["labels"]]
VERBS = ["hold", "go to", "check", "breach", "smoke", "watch", "push", "move to", "cover", "stay at", "get to", "look at", "open",
         "flash", "clear", "take", "jump to", "run to"]
PLACES = ["the door", "the north door", "the south door", "the main door", "the left door", "the door on the left", "the door on the right",
          "the back door", "the other door", "that door", "the door by my pin", "my pin", "the ping", "my mark", "there", "here",
          "that window", "the window", "the east window", "the west window", "the window on the right", "the other window",
          "blue stairs", "the red stairs", "up the blue stairs", "the stairs", "the roof", "the basement", "the second floor",
          "the table", "the chair", "the sofa", "left", "right", "the door behind you", "the door up there", "the door ahead",
          "the window above", "that one", "the far door", "the near window", "where i marked", "the door at my ping",
          "the north door on the second floor", "the window in the basement",
          "right here", "this spot", "this position", "that spot", "over there", "where i'm looking", "upstairs", "downstairs",
          "over here", "that door over there", "this door here"]
SUFFIX = ["", "", "", " on my go", " when i say", " on three"]
NARROW = ["the left one", "the one on the right", "the north one", "that one", "the far one", "the one ahead", "the one behind you",
          "the east one", "the main one", "the one up there", "no, the other one", "the one by my pin", "the near one"]
# what a player says to "Where?": a place and nothing else
POINTING = ["there", "over there", "right there", "at my pin", "my pin", "on my mark", "on the left", "left", "to the right", "behind us",
            "here", "right here", "over here", "up there", "where i'm looking", "that one", "the one i'm looking at", "at the marker",
            "there on my go", "the roof", "upstairs", "the door", "this spot", "hold there", "go to my pin", "it's over there"]
ANSWERS_TXT = {"YES": ["yes", "yeah", "affirmative", "yes that one"], "NO": ["no", "negative", "nope"],
               "MAYBE": ["maybe", "i guess", "up to you"], "DONT_KNOW": ["i don't know", "no idea", "dunno"]}
# orders that name no place: the context may have one
BARE = [("shoot", "OPEN_FIRE"), ("shoot shoot shoot", "OPEN_FIRE"), ("open fire", "OPEN_FIRE"), ("suppress", "SUPPRESS"), ("attack", "ATTACK"),
        ("move up", "MOVE_TO"), ("move", "MOVE_TO"), ("check it", "CHECK"), ("push", "ENTRY"), ("flank", "FLANK"), ("frag", "FRAG"),
        ("watch it", "HOLD_ANGLE"), ("look", "LOOK_AT"), ("shoot on my go", "OPEN_FIRE"), ("move up on my go", "MOVE_TO"), ("stay", "HOLD_POSITION"),
        ("jump", "JUMP"), ("take cover", "TAKE_COVER")]
# lines about the previous order
AFTER = ["again", "shoot again", "do it again", "once more", "one more time", "again there", "no", "no no no", "nope", "wrong",
         "no, here", "no, there", "no, on my pin", "not there, on my pin", "no, here, on my pin", "no again", "negative, left",
         "on my pin", "at my mark", "over there", "there", "here", "right here", "left", "to the right", "behind us", "up there",
         "should there", "sure here", "shoe there", "what there", "the roof", "that door", "no the other door"]
PLAIN = [("go", "GO_NOW"), ("go go go", "GO_NOW"), ("wait", "WAIT"), ("hold on", "WAIT"), ("don't go", "MOVE_TO"), ("never mind", "NONE"),
         ("contact left", "NONE"), ("go prone", "PRONE"), ("get down", "CROUCH"), ("get up", "STAND_UP"), ("revive me", "REVIVE_ME"),
         ("plant it", "PLANT"), ("defuse", "DEFUSE"), ("vault the window", "VAULT_WINDOW"), ("open it", "OPEN"), ("hold fire", "HOLD_FIRE"),
         ("don't shoot", "HOLD_FIRE"), ("follow me", "FOLLOW_ME"), ("come back", "COME_BACK"), ("hold position", "HOLD_POSITION")]


def bare_world(rng):
    """A map without named places: what the game can still give is the thing under the crosshair, the things the
    conversation settled before, and the pin."""
    w = W.empty_world()
    for i in range(rng.choice([0, 1, 1, 1, 2, 3])):
        w["entities"].append({
            "id": f"gaze_{i}", "object": None, "qualifier": None, "zone": None,
            "bearing": float(rng.choice([0, 0, 0, 5, -35, 40, 90, -90, 180])), "distance": float(rng.choice([2, 6, 12, 30, 80])),
            "elevation": float(rng.choice([0.0, 0.0, 0.3, 3.0, -3.0])), "tags": []})
    ids = [e["id"] for e in w["entities"]]
    if rng.random() < 0.6:
        w["player_pin"] = {"id": "pin", "entity": None, "bearing": float(rng.choice([0, 30, -45, 60, 150])), "distance": float(rng.choice([3, 9, 12, 25])), "elevation": 0.0}
    if ids and rng.random() < 0.8:
        w["player_gaze"] = ids[0]
    w["player"]["downed"] = rng.random() < 0.1
    w["bot"]["stance"] = rng.choice(W.STANCES)
    return w


def moved_on(rng, world):
    """The world as the game sends it before the next line."""
    w = json.loads(json.dumps(world))
    w["bot_pin"] = None      # the game's own; the planner's mark of where the bot goes is not sent back
    if w.get("time") is not None:
        w["time"] = round(w["time"] + rng.choice([0.5, 1.5, 3.0, 6.0, 7.9, 8.0, 8.1, 12.0, 30.0, 90.0]), 3)
        w["bot"]["busy"] = rng.random() < 0.25
    ids = [e["id"] for e in w["entities"]]
    r = rng.random()
    if r < 0.08:
        w["player_pin"] = None
    elif r < 0.22:
        old = w.get("player_pin") or {}
        w["player_pin"] = {"id": old.get("id", "pin"), "entity": rng.choice(ids + [None, None, None]) if ids else None,
                           "bearing": float(rng.choice([0, 30, -45, 60, 150])), "distance": float(rng.choice([3, 9, 12, 25])), "elevation": 0.0}
    r = rng.random()
    if r < 0.15:
        w["player_gaze"] = rng.choice(ids + [None]) if ids else None
    for e in w["entities"]:      # somebody walks into the crosshair, or out of it
        if e["object"] is None and rng.random() < 0.1:
            e["tags"] = [] if "enemy" in e["tags"] else e["tags"] + ["enemy"]
    return w


def random_world(rng):
    if rng.random() < 0.3:
        return bare_world(rng)
    w = W.empty_world()
    n = rng.choice([0, 1, 2, 2, 3, 3, 4, 5, 6])
    for i in range(n):
        obj = rng.choice(list(OBJECTS) + [None])
        qual = rng.choice(OBJECTS[obj] + [None, None]) if obj and OBJECTS[obj] else None
        w["entities"].append({
            "id": f"{obj or 'thing'}_{i}", "object": obj, "qualifier": qual,
            "zone": rng.choice(ZONES + [None, None]),
            "bearing": float(rng.choice([0, 5, -35, 40, -60, 70, 90, -90, 120, -150, 180, 179, -179, 25, -25])),
            "distance": float(rng.choice([1, 2, 4, 6, 8, 8, 11, 12, 14, 20, 30, 7.5, 8.5])),
            "elevation": float(rng.choice([0.0, 0.0, 0.0, 0.0, 3.0, -3.0, 1.5, -1.5, 1.4])),
            "tags": rng.sample(TAGS, rng.choice([0, 0, 1, 2]))})
    # twins: a second entity of the same kind at a similar distance, so that the question branch is exercised
    for e in list(w["entities"]):
        if e["object"] and rng.random() < 0.45:
            t = json.loads(json.dumps(e))
            t["id"] = e["id"] + "_twin"
            t["qualifier"] = rng.choice(OBJECTS[e["object"]] + [None]) if OBJECTS[e["object"]] else None
            t["bearing"] = float(rng.choice([-70, -30, 30, 70, 110, -110, 0, 180]))
            t["distance"] = float(e["distance"]) * rng.choice([1.0, 1.1, 1.3, 1.49, 1.5, 2.0])
            w["entities"].append(t)
    ids = [e["id"] for e in w["entities"]]
    if rng.random() < 0.7:
        on = rng.choice(ids + [None, None]) if ids else None
        w["player_pin"] = {"id": "pin_1", "entity": on, "bearing": float(rng.choice([0, 30, -45, 60, 150])), "distance": float(rng.choice([3, 9, 12, 25])), "elevation": 0.0}
    if ids and rng.random() < 0.5:
        w["player_gaze"] = rng.choice(ids)
    w["player"]["downed"] = rng.random() < 0.15
    w["bot"]["stance"] = rng.choice(W.STANCES)
    w["bot"]["items"] = rng.choice([[], [], ["bomb"], ["bomb", "rope"]])
    return w


def probs_for(rng, labels, intent, conf):
    """A float32 row with the intent on top at about conf, the rest spread (under the family gate the family mass is a
    little more)."""
    row = [0.0] * len(labels)
    rest = 1.0 - conf
    others = [j for j in range(len(labels)) if labels[j] != intent]
    weights = [rng.random() ** 3 for _ in others]
    s = sum(weights) or 1.0
    for j, wgt in zip(others, weights):
        row[j] = f32(rest * wgt / s)
    row[labels.index(intent)] = f32(conf)
    return row


def scenario(rng, n_steps, gate, threshold):
    bot = Fake(gate, threshold)
    world = random_world(rng)
    if rng.random() < 0.8:
        world["time"] = float(rng.choice([0.0, 12.5, 100.0, 3600.0]))      # the game's clock: without it there is no context
        world["bot"]["busy"] = False
    pl = W.Planner(bot, world)
    steps = []
    now = world
    for i in range(n_steps):
        if i:
            now = moved_on(rng, now)
            pl.set_world(now)
        r = rng.random()
        frame = pl.memory["frame"]
        if pl.memory["question"] is None and frame is not None and r < 0.3:
            # a line about the previous order: read by the classifier as that order, as another one, or not at all
            text = rng.choice(AFTER)
            intent = rng.choice([frame["intent"], rng.choice(PLACE_ORDERS), "NONE", "NONE"] + [a for a in ("NO", "WAIT") if a in CFG["labels"]])
        elif pl.memory["question"] is None and r < 0.45:
            text, intent = rng.choice(BARE)
            if intent not in CFG["labels"]:
                intent = "NONE"
        elif pl.memory["question"] is not None and pl.memory["question"]["kind"] == "missing" and r < 0.6:
            # "Where?": the player points, says yes, says go, or gives up
            r2 = rng.random()
            if r2 < 0.6:
                text, intent = rng.choice(POINTING), rng.choice(PLACE_ORDERS + ["NONE", "NONE", pl.memory["question"]["intent"]])
            elif r2 < 0.75 and ANSWER_LABELS:
                intent = rng.choice(ANSWER_LABELS)
                text = rng.choice(ANSWERS_TXT[intent])
            else:
                text, intent = rng.choice([("go", "GO_NOW"), ("now", "GO_NOW"), ("wait", "WAIT")])
        elif pl.memory["question"] is not None and r < 0.55:
            if ANSWER_LABELS and rng.random() < 0.6:
                intent = rng.choice(ANSWER_LABELS)
                text = rng.choice(ANSWERS_TXT[intent])
            else:
                text, intent = rng.choice(NARROW), rng.choice(PLACE_ORDERS)
        elif r < 0.65:
            text = f"{rng.choice(VERBS)} {rng.choice(PLACES)}{rng.choice(SUFFIX)}"
            intent = rng.choice(PLACE_ORDERS + [rng.choice(ORDERS)])
        elif r < 0.8:
            text, intent = rng.choice(PLAIN)
            if intent not in CFG["labels"]:
                intent = "NONE"
        elif r < 0.9 and ANSWER_LABELS:
            intent = rng.choice(ANSWER_LABELS)
            text = rng.choice(ANSWERS_TXT[intent])
        else:
            text, intent = rng.choice(NARROW), rng.choice(PLACE_ORDERS + ["NONE"])
        # keep the adjusted confidence 0.02 away from the threshold, and from the bound under which a line is read for
        # its place alone
        for _try in range(50):
            conf = rng.choice([0.3, 0.45, 0.55, 0.7, 0.8, 0.85, 0.9, 0.95, 0.97, 0.99])
            probs = probs_for(rng, bot.labels, intent, conf)
            adj, _ = W.apply_priors(probs, bot.labels, pl.world, pl.memory)
            _, c = bot.pick(adj)
            if abs(c - threshold) > 0.02 and abs(c - W.FRAGMENT_UNSURE) > 0.02:
                break
        res = pl.step(text, probs)
        row = step_row(text, probs, res, pl, bot)
        if i:
            row["world"] = now
        steps.append(row)
    return {"world": world, "gate": gate, "threshold": threshold, "steps": steps}


def step_row(text, probs, res, pl, bot):
    q = pl.memory["question"]
    f = pl.memory["frame"]
    # what the planner itself said (a question, a settled order, a stop, an assumed place); the rest is the chat's pick
    said = res["action"] in ("ask", "resolved") or (res["action"] == "negated" and res["say"] == "Copy, stopping.") or \
        (res["order"] is not None and res["order"]["via"] == "pin_default" and res["action"] == "act") or \
        (res["order"] is not None and f is not None and f["g"] is not None and res["action"] == "act" and res["say"] == pl._echo(f["intent"], f["t"], f["g"]))
    return {"text": text, "probs": probs, "action": res["action"], "intent": res["intent"], "prob": f32(res["prob"]),
            "say": res["say"] if said else None, "adjusted": res["probs_adjusted"],
            "frame": None if f is None else {"intent": f["intent"], "has_target": f["t"] is not None,
                                             "entity": f["g"]["entity"] if f["g"] else None, "via": f["g"]["via"] if f["g"] else None,
                                             "time": f["time"]},
            "ground": res["ground"], "order": res["order"],
            "question": None if q is None else {"kind": q["kind"], "intent": q["intent"], "k": q["k"], "other": q["other"],
                                                "queued": q["queued"], "candidates": q["candidates"], "offered": q["offered"]},
            "pending": bot.pending, "pending_entity": pl.pending_entity, "pending_here": pl.pending_here, "pending_near": pl.pending_near,
            "last_entity": pl.memory["last_entity"], "bot_pin": (pl.world.get("bot_pin") or {}).get("entity")}


def refused():
    base = json.loads(json.dumps(W.WORLD_EXAMPLE))
    bad = []
    w = json.loads(json.dumps(base)); w["entities"][0]["object"] = "hatch"; bad.append(("unknown object", w))
    w = json.loads(json.dumps(base)); w["entities"][1]["id"] = w["entities"][0]["id"]; bad.append(("duplicate id", w))
    w = json.loads(json.dumps(base)); w["entities"][0]["bearing"] = 181.0; bad.append(("bearing out of range", w))
    w = json.loads(json.dumps(base)); w["entities"][0]["bearing"] = -180.0; bad.append(("bearing -180", w))
    w = json.loads(json.dumps(base)); w["entities"][0]["distance"] = -1.0; bad.append(("negative distance", w))
    w = json.loads(json.dumps(base)); w["bot"]["stance"] = "sitting"; bad.append(("unknown stance", w))
    w = json.loads(json.dumps(base)); w["player_gaze"] = "nothing"; bad.append(("gaze on an unknown entity", w))
    w = json.loads(json.dumps(base)); w["player_pin"]["entity"] = "nothing"; bad.append(("pin on an unknown entity", w))
    w = json.loads(json.dumps(base)); w["entities"][0]["qualifier"] = "purple"; bad.append(("unknown qualifier", w))
    w = json.loads(json.dumps(base)); w["entities"][0]["zone"] = "attic"; bad.append(("unknown zone", w))
    w = json.loads(json.dumps(base)); w["time"] = -1.0; bad.append(("negative time", w))
    rows = []
    for why, w in bad:
        try:
            W.validate_world(w)
            ok = True
        except AssertionError:
            ok = False
        rows.append({"refused": why, "world": w, "accepted": ok})
    rows.append({"refused": "the example world (accepted)", "world": base, "accepted": True})
    return rows


def main():
    vocab_mine = {k: v for k, v in json.load(io.open(os.path.join(COOP, "locations.json"), encoding="utf-8")).items() if not k.startswith("_")}
    assert vocab_mine == VOC, "the bot's intent_config.json carries another vocabulary than locations.json: export_cpp.py --config-only first"
    rng = random.Random(54)
    rows = []
    # the example world and the scripted check first: readable failures
    bot = Fake("top", 0.6)
    pl = W.Planner(bot, W.WORLD_EXAMPLE)
    steps = []
    for text, intent, _ in W.DEV:
        if intent not in CFG["labels"]:
            continue
        probs = probs_for(rng, bot.labels, intent, 0.9)
        res = pl.step(text, probs)
        steps.append(step_row(text, probs, res, pl, bot))
    rows.append({"world": W.WORLD_EXAMPLE, "gate": "top", "threshold": 0.6, "steps": steps})
    # ... and the scripted check of a world without named places
    bot = Fake("top", 0.6)
    pl = W.Planner(bot, W.WORLD_BARE)
    steps = []
    for text, intent, _ in W.DEV_BARE:
        if intent not in CFG["labels"]:
            continue
        probs = probs_for(rng, bot.labels, intent, 0.9)
        res = pl.step(text, probs)
        steps.append(step_row(text, probs, res, pl, bot))
    rows.append({"world": W.WORLD_BARE, "gate": "top", "threshold": 0.6, "steps": steps})
    # ... and of the short context: the owner's lines of the first live test
    bot = Fake("top", 0.6)
    pl = W.Planner(bot, W.WORLD_TALK)
    steps = []
    for text, intent, _, *change in W.DEV_TALK:
        if intent not in CFG["labels"]:
            continue
        low = W.talk_change(pl, change[0]) if change else False
        probs = probs_for(rng, bot.labels, intent, 0.45 if low else 0.9)
        before = json.loads(json.dumps(pl.world))
        res = pl.step(text, probs)
        row = step_row(text, probs, res, pl, bot)
        row["world"] = before
        steps.append(row)
    rows.append({"world": W.WORLD_TALK, "gate": "top", "threshold": 0.6, "steps": steps})
    for i in range(600):
        gate = "family" if i % 3 == 2 else "top"
        rows.append(scenario(rng, rng.choice([3, 6, 10, 16]), gate, rng.choice([0.5, 0.6, 0.66, 0.78])))
    n_steps = sum(len(r["steps"]) for r in rows)
    actions = {}
    for r in rows:
        for s in r["steps"]:
            actions[s["action"]] = actions.get(s["action"], 0) + 1
    with io.open(os.path.join(OUT, "world_tests.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        for r in refused():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    grounded = {}
    for r in rows:
        for s in r["steps"]:
            for g in s["ground"]:
                grounded[(g["status"], g["via"])] = grounded.get((g["status"], g["via"]), 0) + 1
    print(f"world tests: {len(rows)} scenarios, {n_steps} steps; actions " + ", ".join(f"{a} {n}" for a, n in sorted(actions.items())))
    print("  groundings: " + ", ".join(f"{s}/{v} {n}" for (s, v), n in sorted(grounded.items(), key=lambda kv: -kv[1])))
    print(f"  priors applied on {sum(s['adjusted'] for r in rows for s in r['steps'])} steps; {len(refused()) - 1} worlds to refuse")
    bare = [r for r in rows if not any(e.get("object") or e.get("zone") for e in r["world"]["entities"])]
    here = sum(1 for r in rows for s in r["steps"] if s["order"] and s["order"]["via"] == "here")
    pointed = sum(1 for r in rows for s in r["steps"] if s["action"] == "resolved" and s["say"] and s["say"].startswith("Got it.") and
                  s["order"] and s["order"]["via"] in ("gaze", "pin", "direction", "here", "memory", "zone"))
    ctx = collections.Counter()
    for r in rows:
        for st in r["steps"]:
            o = st["order"]
            if st["action"] == "negated" and st["say"] == "Copy, stopping.":
                ctx["a bare no stopped the bot"] += 1
            if o is None:
                continue
            if o["via"] == "pin_default":
                ctx["the standing pin as the place not said"] += 1
            if st["action"] == "resolved" and st["say"] and st["say"].startswith("Got it. ") and st["say"].endswith((", there.", ", on your pin.", ", here.", ", to the left.", ", to the right.", ", back.", ", up.", ", down.", ", forward.")):
                ctx["corrections and fragments"] += 1
            elif st["action"] == "resolved" and st["say"] and not st["say"].startswith(("Got it", "I'll take", "Copy", "Which")):
                ctx["repeats"] += 1
    print("  the short context: " + ", ".join(f"{k} {v}" for k, v in sorted(ctx.items())) +
          f"; {sum(1 for r in rows if r['world'].get('time') is None)} scenarios without the game's clock")
    print(f"  {len(bare)} scenarios in a world without named places; {here} orders at \"here\"; {pointed} questions answered by pointing; "
          f"{sum(1 for r in rows for s in r['steps'] if s['pending_here'])} steps with a queued order at \"here\"")


if __name__ == "__main__":
    main()
