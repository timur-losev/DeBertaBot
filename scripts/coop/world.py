"""
The brain's tier 0 (HANDOFF.md, "brains"): the world the bot acts in, without UE5 -- a world state the game fills,
and three things built on it that cost no model time:

  grounding   a place record (locations.record: "the door on the left", "stay at my pin", "that window") resolved to
              the entities of the world state: which door, which pin, where the player looks. One candidate: resolved.
              Several and nothing to tell them apart: ambiguous -- the planner asks. None: missing -- the planner asks.
  memory      what the conversation already settled: the last place resolved, the last order, the question the bot
              asked. "there" without a gaze is the last place; "the other door" is not the last door.
  priors      what the world makes unlikely: a bot already prone does not "go prone"; a window order without a window in
              sight; "revive me" from a player who is up; an answer when nothing was asked. Multipliers on the
              classifier's probabilities before the gate, not renormalized: they never raise a probability.

The world state is what the game side hands the bot before every line (a JSON object, see WORLD_EXAMPLE), with bearings
in degrees in the player's view (0 ahead, positive to the right, (-180, 180]), distances in metres, elevation in metres
above the player. Entities carry the vocabulary's object ids (locations.json) and optional qualifier and zone: the game
tags its actors with the same names the map callouts use.

Everything here is deterministic and the C++ engine follows it step by step (cpp/coop_intent/src/world.cpp), checked
line by line (gen_world_tests.py -> coop_cli --world-tests).
"""
import copy, io, json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import locations as LOC  # noqa: E402

# a direction word accepts a sector of bearings, with overlaps: a door at -40 degrees is "ahead" and "on the left"
SECTORS = {"left": (-150.0, -20.0), "right": (20.0, 150.0), "forward": (-60.0, 60.0)}
BACK_FROM = 120.0          # "back", "behind": |bearing| >= 120
ELEVATION = 1.5            # "up" / "down": elevation beyond +-1.5 m
CLEARLY_NEARER = 1.5       # the nearest candidate wins outright when the next one is 1.5 times as far
# things the bot fetches or rides (bot v55, locations.json version 6): "go find ammo", "grab a gun", "get in the car" mean
# the nearest one, never a question ("Which ammo?")
FETCHED = ("ammo", "weapon", "health", "car")
RELATIVE_ZONES = ("up", "down")   # "upstairs", "downstairs": a floor named by where it is from the speaker
STOREY = 1.5               # ... the next floor that way: the places within 1.5 m of the nearest one in height
STANCES = ("stand", "crouch", "prone")

# the priors: label -> [(condition, multiplier)]; a condition is one of the CONDITIONS below. The game can tune the
# numbers; the engine carries the same table (world.cpp DefaultPriors). The first table had 0.4 ... 0.7; the
# simulation of stt/priors_v54.py (the teachers' out-of-fold probabilities, 810 lines, worlds drawn consistent with
# the truth and worlds drawn blind) showed 0.75 keeps the whole gain of the consistent world (+0.5 criterion, 2-4
# picks changed) and almost none of the cost of a wrong world (-0.1 ... -0.4 instead of -4 ... -5): the gate
# already sits near 0.68, so a mild push is all a prior needs.
PRIOR_X = 0.75
PRIORS = {
    "CROUCH": [("stance=crouch", PRIOR_X)],
    "PRONE": [("stance=prone", PRIOR_X)],
    "STAND_UP": [("stance=stand", PRIOR_X)],
    "VAULT_WINDOW": [("no_object=window", PRIOR_X)],
    "OPEN": [("no_object=door", PRIOR_X)],
    "GET_IN": [("no_object=car", PRIOR_X)],
    "DEFUSE": [("no_tag=bomb", PRIOR_X)],
    "PLANT": [("bot_without=bomb", PRIOR_X)],
    "REVIVE_ME": [("player_up", PRIOR_X)],
    "YES": [("no_question", PRIOR_X)], "NO": [("no_question", PRIOR_X)],
    "MAYBE": [("no_question", PRIOR_X)], "DONT_KNOW": [("no_question", PRIOR_X)],
}
CONDITIONS = ("stance=", "no_object=", "no_tag=", "bot_without=", "player_up", "no_question")
ZONES = sorted({v[1] for v in LOC.VOCAB["phrases"].values() if v[0] in ("zone", "zone_end")})

# ---- a world without named places (a map nobody has marked yet: the pin, the crosshair, directions and the two
# people are all the bot has). The rules below are about the WORDS of the line, so they live with the brain:
#   near and far  "here" is where the speaker is, not what the crosshair is on ("stay here" with the crosshair on a
#                 wall 40 m away). A lone this-pointer in a line with "here" and no far word is grounded "here": no
#                 entity. "this ..." without a far word is near too: the order says so ("near") and the game decides
#                 ("hold this spot" stays, "check this" goes to the crosshair).
#   an answer     the bot asked "Where?" and the player points: "there", "over there", "at my pin", "on the left",
#                 "that one". Such a line is the place of the order the bot asked about, not a new order, even where
#                 the classifier reads a verb into it ("over there" alone looks like MOVE_TO): it starts with a
#                 place word and is short.
NEAR_WORDS = ("here",)
NEAR_DET = ("this", "these")
FAR_WORDS = ("there", "that", "those", "looking", "pointing", "aiming", "facing")
ANSWER_LEADS = ("there", "here", "over", "at", "on", "in", "by", "near", "to", "the", "that", "this", "those", "these", "my",
                "right", "left", "behind", "up", "down", "where", "it", "its", "one", "ahead", "forward", "back", "straight",
                "around", "next", "beside", "above", "below", "under", "inside", "outside", "toward", "towards", "just")
ANSWER_MAX_TOKENS = 6
# what the bot calls a floor it has no place for ("I can't find the roof.")
ZONE_NAMES = {"basement": "the basement", "floor_1": "the first floor", "floor_2": "the second floor",
              "top_floor": "the top floor", "roof": "the roof", "up": "the way up", "down": "the way down"}


def words(text):
    return [t[0] for t in LOC.tokenize(text)] if text else []


def deixis(text):
    """"here" (the line says here and nothing far), "near" (this / these and nothing far), or None."""
    w = words(text)
    if any(x in w for x in FAR_WORDS):
        return None
    if any(x in w for x in NEAR_WORDS):
        return "here"
    if any(x in w for x in NEAR_DET):
        return "near"
    return None


def elliptical(text):
    """A short line that starts with a place word: an answer to "Where?", not an order."""
    w = words(text)
    return bool(w) and len(w) <= ANSWER_MAX_TOKENS and w[0] in ANSWER_LEADS


def usable(g):
    """A grounding the game can act on: an entity, a direction, "here", or a floor that has places."""
    return g["status"] == "resolved" and (g["entity"] is not None or g["via"] in ("direction", "here") or
                                          (g["via"] == "zone" and bool(g["candidates"])))


# ---- a short context. The bot keeps ONE frame of the order it took last (what, where, when) and reads the next line
# against it before it reads it as a new order. Nothing here is a model; the world state gives the time ("time",
# seconds) and whether the bot is still carrying that order out ("bot": {"busy": true}). A game that sends no time
# gets no context: every line is read alone, as before.
#   a place not said   "Shoot!" names no place. For an order that needs one it is, in this order: nothing, if the
#                      crosshair is on an enemy and the order is to fire (the game takes that enemy); the place of the
#                      same order a moment ago; the standing pin. The pin is world state, not memory: it does not age.
#                      A grenade is never thrown at a guessed place.
#   here, by the verb  "come here" is the speaker; "shoot here", "look here", "check here" is the crosshair's point.
#   a correction       "No, here, on my pin.": the previous order, at the place the line names. A bare "no" stops.
#   a repeat           "Shoot again", "again", "once more": the previous order as it was.
#   a fragment         "On my pin.", "over there", "left": a place and no action is the previous order's new place.
#                      So is a line the classifier could not read when its place is clear ("Should there." heard for
#                      "Shoot there"): the conversation moves on instead of "say again".
# The frame lives while the bot is busy with it and CONTEXT_SECONDS after.
CONTEXT_SECONDS = 8.0
FRAGMENT_UNSURE = 0.5      # a line under the threshold AND under this is read for its place alone
FIRE = ("OPEN_FIRE", "SUPPRESS", "ATTACK")                       # the enemy under the crosshair comes first
PIN_DEFAULT = FIRE + ("MOVE_TO", "CHECK", "ENTRY", "FLANK")      # a place not said is the standing pin
CARRY = PIN_DEFAULT + ("HOLD_ANGLE", "LOOK_AT")                  # ... or where the same order was a moment ago
POINTED_HERE = FIRE + ("FRAG", "FLASH", "SMOKE", "LOOK_AT", "CHECK", "HOLD_ANGLE")   # "here" is the crosshair's point
PLACE_INTENTS = CARRY + ("FRAG", "FLASH", "SMOKE", "HOLD_POSITION", "JUMP", "TAKE_COVER", "FALL_BACK", "COME_BACK",
                         "BREACH", "VAULT_WINDOW", "OPEN")       # orders that can be given again at another place
NO_LEADS = ("no", "nope", "nah", "not", "negative", "wrong")
DIRECTION_WORDS = {"left": "to the left", "right": "to the right", "forward": "forward", "back": "back", "up": "up",
                   "down": "down"}


def says_again(w):
    """"again", "once more", "one more time" among the words of the line."""
    return "again" in w or any(a in ("once", "one") and b == "more" for a, b in zip(w, w[1:]))


# ---- a line of several orders. The decoder in front of the classifier (cpp/coop_intent, rewriter.h) writes "smoke
# the door then go in" as two order lines, "smoke the door" and "go in through the door", and each goes through
# step() as a line of its own; the second and later ones with continued=True. Two things follow from their being ONE
# line of the player:
#   the same place   a place a further order names as the order before it did, in the same words or in fewer, is that
#                    place: the door to go in through is the door that got the smoke. It matters most where the place
#                    had to be asked about: two doors ("Which door?", "yes"), or none marked ("I see no door. Where?",
#                    "there"). Without this the bot asks the same question again for the second order.
#   the other one    "the other one" in answer to "Which door? The one ahead, 8 m?" is not the door the bot just
#                    offered. The decoder hands it over as "breach the other door"; without a decoder the line names
#                    no place, and the classifier makes nothing of it, a no, or the other angle (_other_one).
def names_again(t, said):
    """A target that names the thing `said` named and adds nothing of its own: the same object, and no side, floor,
    direction, pointer or "other" the first did not have ("the door" after "the door on the left", "the other door"
    after "the other door"; not "the other door" after "the door")."""
    return t["object"] is not None and t["object"] == said["object"] and t["flag"] in (None, said["flag"]) and \
        all(t.get(k) is None or t.get(k) == said.get(k) for k in ("qualifier", "zone", "direction", "pointer"))

WORLD_EXAMPLE = {
    "entities": [
        {"id": "door_a", "object": "door", "qualifier": "north", "zone": "floor_1", "bearing": -35.0, "distance": 8.0, "elevation": 0.0, "tags": ["closed"]},
        {"id": "door_b", "object": "door", "qualifier": None, "zone": "floor_1", "bearing": 70.0, "distance": 11.0, "elevation": 0.0, "tags": []},
        {"id": "win_a", "object": "window", "qualifier": "east", "zone": "floor_1", "bearing": 20.0, "distance": 6.0, "elevation": 0.0, "tags": []},
        {"id": "stairs_blue", "object": "stairs", "qualifier": "blue", "zone": "floor_1", "bearing": 160.0, "distance": 14.0, "elevation": 0.0, "tags": []},
        {"id": "crate_1", "object": None, "qualifier": None, "zone": "floor_1", "bearing": 5.0, "distance": 4.0, "elevation": 0.0, "tags": ["cover"]},
        {"id": "roof_1", "object": None, "qualifier": None, "zone": "roof", "bearing": 0.0, "distance": 20.0, "elevation": 9.0, "tags": []},
    ],
    "player_pin": {"id": "pin_1", "entity": None, "bearing": 60.0, "distance": 12.0, "elevation": 0.0},
    "bot_pin": None,
    "player_gaze": "win_a",
    "player": {"downed": False},
    "bot": {"stance": "stand", "items": ["bomb"]},
}


def empty_world():
    return {"entities": [], "player_pin": None, "bot_pin": None, "player_gaze": None, "player": {"downed": False},
            "bot": {"stance": "stand", "items": []}}


def validate_world(w):
    """The world state the game hands over; raises on anything the rules cannot read."""
    ids = set()
    for e in w.get("entities", []):
        assert isinstance(e.get("id"), str) and e["id"] and e["id"] not in ids, e
        ids.add(e["id"])
        assert e.get("object") is None or e["object"] in LOC.VOCAB["allowed"], e
        assert e.get("qualifier") is None or e["qualifier"] in LOC.VOCAB["lone"], e
        assert e.get("zone") is None or e["zone"] in ZONES, e
        b = float(e.get("bearing", 0.0))
        assert -180.0 < b <= 180.0, e
        assert float(e.get("distance", 0.0)) >= 0.0, e
    for key in ("player_pin", "bot_pin"):
        p = w.get(key)
        if p is not None:
            assert p.get("entity") is None or p["entity"] in ids, p
            b = float(p.get("bearing", 0.0))
            assert -180.0 < b <= 180.0, p
    assert w.get("player_gaze") is None or w["player_gaze"] in ids, w.get("player_gaze")
    assert w.get("bot", {}).get("stance", "stand") in STANCES, w.get("bot")
    assert w.get("time") is None or float(w["time"]) >= 0.0, w.get("time")
    return w


# ---------------------------------------------------------------- geometry

def xy(bearing, distance):
    r = math.radians(bearing)
    return distance * math.sin(r), distance * math.cos(r)


def in_sector(direction, bearing, elevation):
    if direction == "up":
        return elevation >= ELEVATION
    if direction == "down":
        return elevation <= -ELEVATION
    if direction == "back":
        return abs(bearing) >= BACK_FROM
    lo, hi = SECTORS[direction]
    return lo <= bearing <= hi


def on_zone(e, zone):
    """Whether an entity is on the floor the line names. A named floor is the entity's own zone; "upstairs" and
    "downstairs" are any marked floor at least ELEVATION above or below the speaker."""
    if zone in RELATIVE_ZONES:
        return e.get("zone") is not None and in_sector(zone, 0.0, float(e.get("elevation", 0.0)))
    return e.get("zone") == zone


def next_floor(cands):
    """Of places above (or below), the ones on the nearest floor that way: "upstairs" is one floor up, not the roof."""
    if not cands:
        return cands
    near = min(abs(float(e.get("elevation", 0.0))) for e in cands)
    return [e for e in cands if abs(float(e.get("elevation", 0.0))) <= near + STOREY]


def sector_word(e):
    """How the bot describes where an entity is: 'ahead', 'on the left', 'behind you', 'above'."""
    b, el = float(e.get("bearing", 0.0)), float(e.get("elevation", 0.0))
    if el >= ELEVATION:
        return "above"
    if el <= -ELEVATION:
        return "below"
    if abs(b) <= 45.0:
        return "ahead"
    if abs(b) >= 135.0:
        return "behind you"
    return "on the left" if b < 0 else "on the right"


def describe(e):
    return f"{sector_word(e)}, {int(round(float(e.get('distance', 0.0))))} m"


def dist_between(a, b):
    ax, ay = xy(float(a.get("bearing", 0.0)), float(a.get("distance", 0.0)))
    bx, by = xy(float(b.get("bearing", 0.0)), float(b.get("distance", 0.0)))
    return math.hypot(ax - bx, ay - by)


# ---------------------------------------------------------------- grounding

def ground_target(t, world, memory, here=False):
    """One target of a place record -> {"status", "entity", "candidates", "via"}.
    status: resolved (entity, or a direction / "here" / a floor with places, which the planner takes as is),
    ambiguous (candidates in the order the bot would offer them), missing (the line points at something the world
    does not have). here: the line said "here" and nothing far (deixis)."""
    ents = world.get("entities", [])
    by_id = {e["id"]: e for e in ents}
    pin = world.get("player_pin")
    gaze = world.get("player_gaze")
    last = memory.get("last_entity")
    obj, qual, zone, direction, pointer, flag = t["object"], t["qualifier"], t["zone"], t.get("direction"), t.get("pointer"), t["flag"]

    def out(status, entity=None, candidates=(), via=None):
        return {"status": status, "entity": entity, "candidates": list(candidates), "via": via}

    # the pin: the player's marker, or the entity of that kind nearest to it ("the window by my ping")
    if pointer == "pin":
        if pin is None:
            return out("missing", via="pin")
        if obj is None:
            return out("resolved", pin["entity"] or pin["id"], via="pin")
        cands = [e for e in ents if e.get("object") == obj and (qual is None or e.get("qualifier") == qual)]
        if not cands:
            # "the door at my pin" on a map without doors marked: what the pin is on is that door
            return out("resolved", pin["entity"] or pin["id"], via="pin")
        cands.sort(key=lambda e: (dist_between(e, pin), e["id"]))
        return out("resolved", cands[0]["id"], [e["id"] for e in cands], "pin")

    if obj is None:
        if pointer == "this":
            # "here": where the speaker stands, whatever the crosshair is on
            if here and zone is None and direction is None:
                return out("resolved", None, via="here")
            # "there", "that one": where the player looks, else the last place the conversation settled
            if gaze is not None and gaze in by_id:
                return out("resolved", gaze, via="gaze")
            if last is not None and last in by_id:
                return out("resolved", last, via="memory")
            if pin is not None:
                return out("resolved", pin["entity"] or pin["id"], via="pin")     # the one place that is marked
            return out("missing", via="this")
        if zone is not None:
            cands = [e for e in ents if on_zone(e, zone)]
            if zone in RELATIVE_ZONES:
                cands = next_floor(cands)
            if not cands:
                return out("missing", via="zone")    # a floor the world has no place on: the bot cannot find it
            return out("resolved", None, [e["id"] for e in cands], "zone")
        if direction is not None:
            return out("resolved", None, [], "direction")
        return out("missing")

    # an object: the entities of its kind, narrowed by the qualifier, the zone, the direction
    cands = [e for e in ents if e.get("object") == obj]
    if not cands:
        # "that door" where no door is marked: the thing the crosshair is on is that door, if it is not a marked
        # place of another kind
        if pointer == "this" and gaze is not None and gaze in by_id and by_id[gaze].get("object") is None:
            return out("resolved", gaze, via="gaze")
        return out("missing")
    if qual is not None:
        cands = [e for e in cands if e.get("qualifier") == qual]
    if zone is not None:
        cands = [e for e in cands if on_zone(e, zone)]     # "the door upstairs": a door on a floor above
    # "up the blue stairs": up is the way along a vertical object, not where it stands
    if direction is not None and not (direction in ("up", "down") and obj in LOC.VOCAB["vertical"]):
        cands = [e for e in cands if in_sector(direction, float(e.get("bearing", 0.0)), float(e.get("elevation", 0.0)))]
    if flag == "other" and last is not None:
        cands = [e for e in cands if e["id"] != last]
    if not cands:
        return out("missing")
    cands.sort(key=lambda e: (float(e.get("distance", 0.0)), e["id"]))
    ids = [e["id"] for e in cands]
    if pointer == "this" and gaze in ids:
        return out("resolved", gaze, ids, "gaze")
    if len(cands) == 1:
        return out("resolved", ids[0], ids, "only")
    if flag == "unknown_modifier":
        # "the back door": the player singled one out in a way the map names cannot express; never the nearest
        return out("ambiguous", None, ids, "unknown_modifier")
    if obj in FETCHED or float(cands[1].get("distance", 0.0)) >= CLEARLY_NEARER * float(cands[0].get("distance", 0.0)):
        return out("resolved", ids[0], ids, "nearest")
    return out("ambiguous", None, ids, "distance")


def ground(record, world, memory, text=None, intent=None):
    """Every target of locations.record(); the primary's grounding is what the order needs. text: the line, for
    "here" (without it a this-pointer is the crosshair, as for a queued order grounded again on the go). intent: the
    order the line gives: "here" is the speaker's place for "come here" and the crosshair's point for "shoot here"."""
    here = deixis(text) == "here" and intent not in POINTED_HERE
    return [ground_target(t, world, memory, here) for t in record["targets"]]


# ---------------------------------------------------------------- priors

def condition_holds(cond, world, memory):
    bot = world.get("bot", {})
    if cond.startswith("stance="):
        return bot.get("stance", "stand") == cond[7:]
    if cond.startswith("no_object="):
        return not any(e.get("object") == cond[10:] for e in world.get("entities", []))
    if cond.startswith("no_tag="):
        return not any(cond[7:] in e.get("tags", []) for e in world.get("entities", []))
    if cond.startswith("bot_without="):
        return cond[12:] not in bot.get("items", [])
    if cond == "player_up":
        return not world.get("player", {}).get("downed", False)
    if cond == "no_question":
        return memory.get("question") is None
    raise ValueError(cond)


def apply_priors(probs, labels, world, memory, priors=PRIORS):
    """(the row with the multipliers that hold; whether any held). NOT renormalized: a prior only lowers what the
    world makes unlikely, it never lifts another intent over the threshold (renormalizing did, in the simulation of
    priors_v54.py: a callout became an order because the mass it lost went to the others)."""
    out = list(probs)
    changed = False
    for j, label in enumerate(labels):
        for cond, x in priors.get(label, ()):
            if condition_holds(cond, world, memory):
                out[j] *= x
                changed = True
    return out, changed


# ---------------------------------------------------------------- the planner: memory, questions, orders

ANSWER_YES, ANSWER_NO, ANSWER_UNSURE = "YES", "NO", ("MAYBE", "DONT_KNOW")
OTHER_ANGLE = "HOLD_OTHER_ANGLE"     # what the classifier makes of a bare "the other one"


def new_memory():
    # frame: the order taken last -- {"intent", "t" (its place target or None), "g" (that target's grounding or None),
    # "other", "near", "time", "said" (what the order's own line called the place, when the place came from the answer
    # to "Where?": the door of "smoke the door", where "t" is the "there" that answered; else None)}
    return {"last_entity": None, "last_order": None, "question": None, "frame": None}


# the place of an order whose line named none: the standing pin, as if the line had said "my pin"
PIN_TARGET = {"object": None, "qualifier": None, "zone": None, "direction": None, "pointer": "pin", "role": None,
              "flag": None}
# ... and of a line whose words were lost while its pointing was not ("Should there." heard for "Shoot there")
THIS_TARGET = dict(PIN_TARGET, pointer="this")
LOST_POINTERS = ("there", "here")


def object_word(record, k, world):
    t = record["targets"][k]
    return t["object"] or "place"


class Planner:
    """Wraps a bot (coop_bot.Bot or anything with labels, decide(text, probs), pending): the same decision, then
    the world. Returns per line a dict:
      action    the bot's action, or "ask" (a question is pending), "resolved" (the answer settled it)
      say       what the bot says
      ground    the grounding of every target of the line's places
      order     when the game gets something to do: {"intent", "entity", "candidates", "direction", "zone", "pointer",
                "other", "via" (how the place was found: "gaze", "pin", "here", "direction", ...), "near" (the line
                pointed with "this" / "here" and no far word)}
      question  the pending question after this line, or None
    """

    def __init__(self, bot, world=None, priors=PRIORS):
        self.bot = bot
        self.world = validate_world(copy.deepcopy(world) if world else empty_world())
        self.memory = new_memory()
        self.priors = priors
        self.pending_entity = None     # the queued order's resolved entity
        self.pending_here = False      # ... or that its place is "here"
        self.pending_near = False      # ... and that it pointed with "this" / "here"
        self.frame_in_line = False     # the frame is of an order of the line being read (step(..., continued=True))

    def set_world(self, world):
        self.world = validate_world(copy.deepcopy(world))

    def reset(self):
        self.bot.reset()
        self.memory = new_memory()
        self._drop_pending()
        self.frame_in_line = False

    def _drop_pending(self):
        self.pending_entity, self.pending_here, self.pending_near = None, False, False

    def _alive(self, f):
        """The previous order is still what the conversation is about: the bot is busy with it, or it was given
        seconds ago."""
        now = self.world.get("time")
        if f is None or now is None or f["time"] is None:
            return False
        return bool(self.world.get("bot", {}).get("busy", False)) or 0.0 <= float(now) - f["time"] <= CONTEXT_SECONDS

    def _known(self, g):
        """A grounding kept from an earlier line still points at something the world has."""
        if g["entity"] is None:
            return True
        pin = self.world.get("player_pin")
        return any(e["id"] == g["entity"] for e in self.world["entities"]) or \
            (pin is not None and g["entity"] in (pin["id"], pin["entity"]))

    def _where(self, t, g):
        """How the bot names a place it took from the context."""
        if g is None:
            return ""
        pin = self.world.get("player_pin")
        if g["via"] in ("pin", "pin_default") or (pin is not None and g["entity"] is not None and g["entity"] in (pin["id"], pin["entity"])):
            return "on your pin"
        if g["via"] == "here":
            return "here"
        if g["entity"] is not None:
            return "there"
        return DIRECTION_WORDS.get(t.get("direction") if t else None, "")

    def _echo(self, intent, t, g):
        """What the bot says when the place of the order came from the context: the order and where."""
        phrase, where = self.bot.phrase[intent].capitalize(), self._where(t, g)
        return f"{phrase}, {where}." if where else f"{phrase}."

    def _default_place(self, intent):
        """The place of an order whose line names none: (target, grounding) or None."""
        by_id = {e["id"]: e for e in self.world["entities"]}
        gaze = self.world.get("player_gaze")
        if intent in FIRE and gaze in by_id and "enemy" in by_id[gaze].get("tags", []):
            return None      # the game takes the enemy under the crosshair
        f = self.memory["frame"]
        if intent in CARRY and f is not None and f["intent"] == intent and f["t"] is not None and self._alive(f) and self._known(f["g"]):
            return f["t"], f["g"]
        pin = self.world.get("player_pin")
        if intent in PIN_DEFAULT and pin is not None:
            return dict(PIN_TARGET), {"status": "resolved", "entity": pin["entity"] or pin["id"], "candidates": [], "via": "pin_default"}
        return None

    def _reissue(self, f, t, g, near, lead):
        """The previous order again, at the place given (its own, or the one the line named)."""
        rec = {"targets": [t], "primary": 0} if t is not None else {"targets": [], "primary": -1}
        order = self._order(f["intent"], rec, [g] if t is not None else [], 0 if t is not None else -1, f["other"], near)
        return "resolved", lead + self._echo(f["intent"], t, g), order

    def _context(self, text, action, intent, prob, record):
        """The line read against the previous order: a correction, a repeat or a fragment of it. Returns
        (action, say, order) or None: the line stands on its own."""
        f = self.memory["frame"]
        w = words(text)
        if f is None or not w:
            return None
        alive = self._alive(f)
        k = record["primary"] if record and record["targets"] else -1
        t = record["targets"][k] if k >= 0 else None
        place = None
        if t is not None and t["role"] is None:
            # the place as the previous order reads it: "here" after "shoot" is the crosshair's point
            g = ground_target(t, self.world, self.memory, deixis(text) == "here" and f["intent"] not in POINTED_HERE)
            if usable(g):
                place = (t, g)
        near = deixis(text) is not None
        unsure = action in ("say_again", "ignore", "answer")
        if t is None and alive and action == "say_again" and prob < FRAGMENT_UNSURE and w[-1] in LOST_POINTERS and                 f["intent"] in PLACE_INTENTS:
            # the place matcher takes "there" only after an order word; here the order word is what was misheard
            g = ground_target(THIS_TARGET, self.world, self.memory, w[-1] == "here" and f["intent"] not in POINTED_HERE)
            if usable(g):
                return self._reissue(f, dict(THIS_TARGET), g, near, "Got it. ")
        if w[0] in NO_LEADS and alive and action != "negated":
            if place is not None and f["intent"] in PLACE_INTENTS:
                return self._reissue(f, place[0], place[1], near, "Got it. ")
            if t is None and unsure:
                self.memory["frame"] = None
                return "negated", "Copy, stopping.", None
        if says_again(w) and place is None and t is None:
            if (unsure and alive) or (action == "act" and intent == f["intent"] and f["t"] is not None and self._known(f["g"])):
                if f["t"] is None or self._known(f["g"]):
                    return self._reissue(f, f["t"], f["g"], f["near"], "")
        if alive and place is not None and f["intent"] in PLACE_INTENTS and \
                ((elliptical(text) and (unsure or action == "act")) or (action == "say_again" and prob < FRAGMENT_UNSURE)):
            return self._reissue(f, place[0], place[1], near, "Got it. ")
        return None

    def _same_place(self, record, grounding):
        """A further order of the line being read: a place it names as the order before it did is that order's place,
        whatever the world would make of the words alone (two doors: a question; "the door" after "the door on the
        right": the nearest; "the other door" twice: the first one again). Only a place that is a thing of the world:
        a direction or "here" is not carried over."""
        f = self.memory["frame"]
        k = record["primary"] if record and record["targets"] else -1
        if f is None or k < 0 or f["g"] is None or f["g"]["entity"] is None or not self._known(f["g"]):
            return
        t = record["targets"][k]
        said = f["said"] or f["t"]
        if t["role"] is not None or said is None or not names_again(t, said):
            return
        grounding[k] = copy.deepcopy(f["g"])

    def _order(self, intent, record, grounding, k, other, near=False, said=None):
        t = record["targets"][k] if k >= 0 else None
        g = grounding[k] if k >= 0 else None
        ent = g["entity"] if g else None
        if ent is not None:
            self.memory["last_entity"] = ent
        self.memory["last_order"] = intent
        if intent != "GO_NOW":      # "go" with nothing queued is not an order to come back to
            now = self.world.get("time")
            self.memory["frame"] = {"intent": intent, "t": t, "g": g, "other": other, "near": bool(near),
                                    "time": float(now) if now is not None else None, "said": said}
            self.frame_in_line = True
        return {"intent": intent, "entity": ent, "candidates": g["candidates"] if g else [],
                "direction": t.get("direction") if t else None, "zone": t["zone"] if t else None,
                "pointer": t.get("pointer") if t else None, "other": other, "via": g["via"] if g else None,
                "near": bool(near and t is not None and t.get("pointer") == "this")}

    def _ask(self, intent, record, grounding, k, other, queued):
        g = grounding[k]
        obj = object_word(record, k, self.world)
        by_id = {e["id"]: e for e in self.world["entities"]}
        if g["status"] == "missing":
            zone = record["targets"][k]["zone"]
            what = {"pin": "I don't see a pin.", "this": "I don't know where you mean.",
                    "zone": f"I can't find {ZONE_NAMES.get(zone, 'that place')}."}.get(g["via"], f"I see no {obj}.")
            self.memory["question"] = {"kind": "missing", "intent": intent, "record": record, "k": k, "other": other,
                                       "queued": queued, "candidates": [], "offered": 0}
            return "ask", what + " Where?"
        cands = g["candidates"]
        self.memory["question"] = {"kind": "which", "intent": intent, "record": record, "k": k, "other": other,
                                   "queued": queued, "candidates": cands, "offered": 0}
        return "ask", f"Which {obj}? The one {describe(by_id[cands[0]])}?"

    def _answer(self, intent):
        """The player's answer to the pending question; returns (action, say, order) or None if the question was not
        of a kind an answer settles."""
        q = self.memory["question"]
        by_id = {e["id"]: e for e in self.world["entities"]}
        if q["kind"] != "which":
            if intent in ANSWER_UNSURE or intent == ANSWER_YES:
                return None      # "yes" to "Where?": step() looks whether the place is there now
            self.memory["question"] = None
            return "resolved", "Copy, never mind.", None
        cands = q["candidates"]
        if intent == ANSWER_YES or intent in ANSWER_UNSURE:
            pick = cands[q["offered"]] if intent == ANSWER_YES else cands[0]
            self.memory["question"] = None
            return self._settle(q, pick, "Got it." if intent == ANSWER_YES else f"I'll take the one {describe(by_id[pick])}.")
        # NO: the next candidate, or give up
        q["offered"] += 1
        if q["offered"] < len(cands):
            return "ask", f"The one {describe(by_id[cands[q['offered']]])}?", None
        self.memory["question"] = None
        return "resolved", "Which one, then? Point at it.", None

    def _other_one(self, q, left, said=None):
        """ "The other one" in answer to "Which door? The one ahead, 8 m?": not the door the bot just offered. left: the
        candidates the line still fits; said: how the line named the place ("the other door"), if it did. One other:
        that one. Several: they are what is left to choose from, and the nearest is offered, as after "no". None: the
        line is something else."""
        left = [c for c in left if c != q["candidates"][q["offered"]]]
        if len(left) == 1:
            self.memory["question"] = None
            return self._settle(q, left[0], "Got it.", said)
        if left:
            by_id = {e["id"]: e for e in self.world["entities"]}
            q["candidates"], q["offered"] = left, 0
            return "ask", f"The one {describe(by_id[left[0]])}?", None
        return None

    def _settle(self, q, entity, say, said=None):
        """The question's order with the entity the player confirmed. said: how the line that settled it named the
        place, when that is not how the order's own line did."""
        grounding = [{"status": "resolved", "entity": entity, "candidates": q["candidates"], "via": "answer"}]
        rec = {"targets": [q["record"]["targets"][q["k"]]], "primary": 0}
        if q["queued"]:
            self.bot.pending, self.bot.pending_places, self.bot.pending_other = q["intent"], q["record"], q["other"]
            self._drop_pending()
            self.pending_entity = entity
            self.memory["last_entity"] = entity
            return "resolved", say + f" Ready to {self.bot.phrase[q['intent']]}. On your go.", None
        return "resolved", say + f" {self.bot.phrase[q['intent']].capitalize()}.", self._order(q["intent"], rec, grounding, 0, q["other"], said=said)

    def _settle_place(self, q, rec, g, queued, near):
        """The "Where?" question's order with the place the player pointed at: rec is that place's record (one
        target), g its grounding."""
        self.memory["question"] = None
        phrase = self.bot.phrase[q["intent"]]
        if queued:
            self.bot.pending, self.bot.pending_places, self.bot.pending_other = q["intent"], rec, q["other"]
            self.pending_entity, self.pending_here, self.pending_near = g["entity"], g["via"] == "here", near
            if g["entity"] is not None:
                self.memory["last_entity"] = g["entity"]
            return "resolved", f"Got it. Ready to {phrase}. On your go.", None
        return "resolved", f"Got it. {phrase.capitalize()}.", \
            self._order(q["intent"], rec, [g], 0, q["other"], near, said=q["record"]["targets"][q["k"]])

    def _place_answer(self, q, text, action, intent, record, grounding):
        """A "Where?" answered by pointing ("there", "at my pin", "on the left", "that one"), or by "yes" / "go" once
        the place the order named is there (the pin was put, the crosshair is on something now). Returns
        (action, say, order) or None: the line is something else."""
        k = record["primary"] if record and record["targets"] else -1
        t = record["targets"][k] if k >= 0 else None
        near = deixis(text) is not None
        if t is not None:
            if t["role"] is None and usable(grounding[k]) and \
                    (action in ("say_again", "ignore", "answer") or
                     (action in ("act", "queued") and (intent == q["intent"] or elliptical(text)))):
                if action == "queued":
                    self.bot.reset()     # the line's own "on my go" queued another order: the question's is queued below
                return self._settle_place(q, {"targets": [t], "primary": 0}, grounding[k], q["queued"] or action == "queued", near)
            return None
        if action == "go" or (action == "answer" and intent == ANSWER_YES):
            t0 = q["record"]["targets"][q["k"]]
            g = ground_target(t0, self.world, self.memory)
            if usable(g):
                return self._settle_place(q, {"targets": [t0], "primary": 0}, g, q["queued"], False)
        return None

    def step(self, text, probs, continued=False):
        """continued: the line is a further order of the line the player just said (see "a line of several orders")."""
        if not continued:
            self.frame_in_line = False
        probs2, adjusted = apply_priors(probs, self.bot.labels, self.world, self.memory, self.priors)
        reply, rec = self.bot.decide(text, probs2)
        action, intent = rec["action"], rec["intent"]
        record = rec["places"]
        grounding = ground(record, self.world, self.memory, text, intent) if record and record["targets"] else []
        if continued and self.frame_in_line:
            self._same_place(record, grounding)
        near = deixis(text) is not None
        out = {"action": action, "say": reply, "ground": grounding, "order": None, "question": None, "intent": intent,
               "prob": rec["prob"], "probs_adjusted": adjusted}
        q = self.memory["question"]

        if q is not None and q["kind"] == "which" and rec["other"] and not (record and record["targets"]) and \
                (action in ("say_again", "ignore") or (action == "answer" and intent == ANSWER_NO) or
                 (action == "act" and intent in (q["intent"], OTHER_ANGLE))):
            # "the other one", "no, the other one": no place said. The classifier reads the words as nothing, as a no,
            # as the order asked about, or as the other angle
            r = self._other_one(q, q["candidates"])
            if r is not None:
                out["action"], out["say"], out["order"] = r
                out["question"] = self.memory["question"]
                return out
        if q is not None and action == "answer":
            r = self._answer(intent)
            if r is not None:
                out["action"], out["say"], out["order"] = r
                out["question"] = self.memory["question"]
                return out
        if q is not None and q["kind"] == "missing":
            r = self._place_answer(q, text, action, intent, record, grounding)
            if r is not None:
                out["action"], out["say"], out["order"] = r
                return out
        if q is not None and q["kind"] == "which" and record and record["targets"] and \
                (action in ("say_again", "ignore") or (action in ("act", "queued") and intent == q["intent"])):
            # a place instead of yes / no: "the left one", "the north door" -- if it narrows the candidates to one. A line
            # the classifier reads as another order is that order, and the question is dropped below
            by_id = {e["id"]: e for e in self.world["entities"]}
            k = record["primary"]
            t = record["targets"][k] if k >= 0 else None
            if t is not None and t["role"] is None:
                left = [c for c in q["candidates"] if
                        (t["object"] is None or by_id[c].get("object") == t["object"]) and
                        (t["qualifier"] is None or by_id[c].get("qualifier") == t["qualifier"]) and
                        (t.get("direction") is None or in_sector(t["direction"], float(by_id[c].get("bearing", 0.0)), float(by_id[c].get("elevation", 0.0)))) and
                        (t.get("pointer") != "this" or self.world.get("player_gaze") in (None, c))]
                if t["flag"] == "other":
                    r = self._other_one(q, left, t)      # "the other door"
                    if r is not None:
                        out["action"], out["say"], out["order"] = r
                        out["question"] = self.memory["question"]
                        return out
                elif len(left) == 1 and (t["object"] is not None or t.get("direction") is not None or t.get("pointer") is not None):
                    self.memory["question"] = None
                    out["action"], out["say"], out["order"] = self._settle(q, left[0], "Got it.")
                    out["ground"] = grounding
                    return out
        if action not in ("say_again",):
            # any other line drops the question (an answer that did not fit it too)
            self.memory["question"] = None

        if q is None:
            # nothing was asked: the line may be about the previous order
            r = self._context(text, action, intent, rec["prob"], record)
            if r is not None:
                out["action"], out["say"], out["order"] = r
                return out
        defaulted = None
        if action in ("act", "queued") and not (record and record["targets"]):
            # an order that names no place: the context may have one
            defaulted = self._default_place(intent)
            if defaulted is not None:
                record = {"targets": [defaulted[0]], "primary": 0}
                grounding = [defaulted[1]]
                out["ground"] = grounding
                if action == "queued":
                    self.bot.pending_places = record     # the queued order goes with the place it was given

        if action in ("act", "queued"):
            k = record["primary"] if record else -1
            if k >= 0 and record["targets"][k]["role"] is None:
                g = grounding[k]
                if g["status"] in ("ambiguous", "missing"):
                    if action == "queued":   # the bot queued it already; the question decides its place
                        self.bot.reset()
                    out["action"], out["say"] = self._ask(intent, record, grounding, k, rec["other"], action == "queued")
                    out["question"] = self.memory["question"]
                    return out
            if action == "act":
                out["order"] = self._order(intent, record, grounding, k, rec["other"], near)
                if defaulted is not None:
                    out["say"] = self._echo(intent, defaulted[0], defaulted[1])     # the bot says what it assumed
            else:
                self._drop_pending()
                if k >= 0:
                    self.pending_entity, self.pending_here, self.pending_near = grounding[k]["entity"], grounding[k]["via"] == "here", near
        elif action == "execute":
            ex = rec["executed_places"]
            k = ex["primary"] if ex and ex["targets"] else -1
            if k >= 0 and (self.pending_entity is not None or self.pending_here):
                # the place the queued order was given, not what the crosshair is on now
                g = [{"status": "resolved", "entity": self.pending_entity, "candidates": [], "via": "here" if self.pending_here else "queued"}]
                rec2 = {"targets": [ex["targets"][k]], "primary": 0}
                out["order"] = self._order(rec["executed"], rec2, g, 0, rec["executed_other"], self.pending_near)
            elif self.pending_entity is not None:
                out["order"] = self._order(rec["executed"], {"targets": [], "primary": -1}, [], -1, rec["executed_other"])
            else:
                g2 = ground(ex, self.world, self.memory) if ex and ex["targets"] else []
                out["order"] = self._order(rec["executed"], ex, g2, k, rec["executed_other"], self.pending_near)
            self._drop_pending()
        elif action == "go":
            out["order"] = self._order("GO_NOW", record, grounding, -1, False)
        elif action in ("wait", "negated"):
            self._drop_pending()
            self.memory["frame"] = None
        if out["order"] and out["order"]["entity"] is not None:
            self.world["bot_pin"] = {"id": "bot_pin", "entity": out["order"]["entity"]}   # the bot marks where it goes
        return out


# ---------------------------------------------------------------- a scripted check (tuning material, not a test set)

DEV = [
    # (world, line, probs-as-intent, what we expect of the planner)
    ("hold the door", "HOLD_ANGLE", {"action": "ask"}),                       # two doors, 8 m and 11 m: not clearly nearer
    ("yes", "YES", {"action": "resolved", "entity": "door_a"}),
    ("hold the door on the right", "HOLD_ANGLE", {"action": "act", "entity": "door_b"}),
    ("hold the other door", "HOLD_ANGLE", {"action": "act", "entity": "door_a"}),
    ("stay at my pin", "HOLD_POSITION", {"action": "act", "entity": "pin_1"}),
    ("check that window", "CHECK", {"action": "act", "entity": "win_a"}),
    ("go there", "MOVE_TO", {"action": "act", "entity": "win_a"}),              # the gaze
    ("go up the blue stairs", "MOVE_TO", {"action": "act", "entity": "stairs_blue"}),
    ("get to the roof", "MOVE_TO", {"action": "act", "zone": "roof"}),
    ("breach the north door on my go", "BREACH", {"action": "queued"}),
    ("go", "GO_NOW", {"action": "execute", "entity": "door_a"}),
    ("hold the door", "HOLD_ANGLE", {"action": "ask"}),
    ("no", "NO", {"action": "ask"}),
    ("no", "NO", {"action": "resolved"}),
    ("hold the door", "HOLD_ANGLE", {"action": "ask"}),
    ("the left one", "HOLD_ANGLE", {"action": "resolved", "entity": "door_a"}),
    ("go to the back door", "MOVE_TO", {"action": "ask"}),                     # unknown_modifier: never the nearest
    ("the one on the right", "MOVE_TO", {"action": "resolved", "entity": "door_b"}),
    ("push the south window", "MOVE_TO", {"action": "ask"}),                  # missing
    ("go prone", "PRONE", {"action": "act"}),
]


# a map nobody has marked: the crosshair is on something 12 m ahead, the pin is 15 m off to the right
WORLD_BARE = {
    "entities": [{"id": "gaze_1", "object": None, "qualifier": None, "zone": None, "bearing": 0.0, "distance": 12.0, "elevation": 0.3, "tags": []}],
    "player_pin": {"id": "pin", "entity": None, "bearing": 35.0, "distance": 15.0, "elevation": 0.0},
    "bot_pin": None, "player_gaze": "gaze_1", "player": {"downed": False}, "bot": {"stance": "stand", "items": []},
}
DEV_BARE = [
    ("stay here", "HOLD_POSITION", {"action": "act", "entity": None, "via": "here"}),        # not the crosshair
    ("hold this spot", "HOLD_POSITION", {"action": "act", "entity": "gaze_1", "near": True}),  # the game keeps it in place
    ("go there", "MOVE_TO", {"action": "act", "entity": "gaze_1", "via": "gaze", "near": False}),
    ("check that door", "CHECK", {"action": "act", "entity": "gaze_1"}),                    # no door is marked: the crosshair
    ("watch the door at my pin", "HOLD_ANGLE", {"action": "act", "entity": "pin"}),
    ("hold the door", "HOLD_ANGLE", {"action": "ask"}),                                     # no pointer: "I see no door. Where?"
    ("over there", "MOVE_TO", {"action": "resolved", "entity": "gaze_1", "intent": "HOLD_ANGLE"}),   # the answer, though it reads as an order
    ("hold the window", "HOLD_ANGLE", {"action": "ask"}),
    ("at my pin", "HOLD_POSITION", {"action": "resolved", "entity": "pin", "intent": "HOLD_ANGLE"}),
    ("check the stairs", "CHECK", {"action": "ask"}),
    ("on the left", "NONE", {"action": "resolved", "direction": "left", "intent": "CHECK"}),
    ("go upstairs", "MOVE_TO", {"action": "ask"}),                                          # "I can't find the way up. Where?"
    ("no", "NO", {"action": "resolved"}),
    ("breach there on my go", "BREACH", {"action": "queued"}),
    ("go", "GO_NOW", {"action": "execute", "entity": "gaze_1"}),
    ("hold here on my go", "HOLD_POSITION", {"action": "queued"}),
    ("go", "GO_NOW", {"action": "execute", "entity": None, "via": "here"}),
    ("frag the window on my go", "FRAG", {"action": "ask"}),
    ("there", "NONE", {"action": "resolved"}),                                              # queued again, at the crosshair
    ("go", "GO_NOW", {"action": "execute", "entity": "gaze_1", "intent": "FRAG"}),
]


# the owner's first live test, 2026-10-10: the lines the bot read literally. A fourth element changes the world before
# the line (time passes, the pin is put, the bot finishes).
PIN_A = {"id": "pin", "entity": None, "bearing": 35.0, "distance": 15.0, "elevation": 0.0}
ENEMY = {"id": "gaze_9", "object": None, "qualifier": None, "zone": None, "bearing": 0.0, "distance": 20.0, "elevation": 0.0, "tags": ["enemy"]}
WORLD_TALK = {
    "entities": [{"id": "gaze_1", "object": None, "qualifier": None, "zone": None, "bearing": 0.0, "distance": 12.0, "elevation": 0.3, "tags": []}],
    "player_pin": None, "bot_pin": None, "player_gaze": "gaze_1", "player": {"downed": False},
    "bot": {"stance": "stand", "items": [], "busy": False}, "time": 100.0,
}
DEV_TALK = [
    ("shoot", "OPEN_FIRE", {"action": "act", "entity": None}),                                   # no pin, no enemy: weapons free
    ("shoot shoot shoot", "OPEN_FIRE", {"action": "act", "entity": "pin", "via": "pin_default"}, {"time": 130.0, "player_pin": PIN_A}),
    ("shoot here", "OPEN_FIRE", {"action": "act", "entity": "gaze_1", "via": "gaze"}, {"time": 160.0}),   # the crosshair, not the speaker
    ("come here", "FOLLOW_ME", {"action": "act", "entity": None, "via": "here"}, {"time": 190.0}),
    ("jump there", "JUMP", {"action": "act", "entity": "gaze_1"}, {"time": 220.0}),
    ("no here on my pin", "WAIT", {"action": "resolved", "entity": "pin", "intent": "JUMP"}, {"time": 223.0, "low": True}),   # the correction
    ("go there", "MOVE_TO", {"action": "act", "entity": "gaze_1"}, {"time": 260.0}),
    ("on my pin", "HOLD_POSITION", {"action": "resolved", "entity": "pin", "intent": "MOVE_TO"}, {"time": 262.0}),   # the fragment
    ("on my pin", "HOLD_POSITION", {"action": "act", "entity": "pin", "intent": "HOLD_POSITION"}, {"time": 300.0}),  # too late: a new order
    ("shoot there", "OPEN_FIRE", {"action": "act", "entity": "gaze_1"}, {"time": 340.0}),
    ("shoot again", "OPEN_FIRE", {"action": "resolved", "entity": "gaze_1", "intent": "OPEN_FIRE"}, {"time": 400.0}),  # a minute later, said so
    ("should there", "CHECK", {"action": "resolved", "entity": "gaze_1", "intent": "OPEN_FIRE"}, {"time": 403.0, "low": True}),  # heard wrong, place clear
    ("should there", "CHECK", {"action": "say_again"}, {"time": 460.0, "low": True}),             # no order to hang it on
    ("suppress", "SUPPRESS", {"action": "act", "entity": None}, {"time": 500.0, "gaze_enemy": True}),   # an enemy under the crosshair wins
    ("frag", "FRAG", {"action": "act", "entity": None}, {"time": 530.0}),                         # never a grenade at a guess
    ("go there", "MOVE_TO", {"action": "act", "entity": "gaze_1"}, {"time": 560.0}),
    ("no", "NO", {"action": "negated"}, {"time": 562.0}),                                         # stop
    ("move up", "MOVE_TO", {"action": "act", "entity": "pin", "via": "pin_default"}, {"time": 600.0}),
    ("move up", "MOVE_TO", {"action": "act", "entity": None}, {"time": 640.0, "player_pin": None}),   # the pin is gone
]


# a building with its floors marked, the speaker on the first floor: the basement 3 m below, the second floor 3.2 m
# above, the roof 6.5 m above
WORLD_FLOORS = {
    "entities": [
        {"id": "base_a", "object": None, "qualifier": None, "zone": "basement", "bearing": 10.0, "distance": 9.0, "elevation": -3.0, "tags": []},
        {"id": "one_a", "object": None, "qualifier": None, "zone": "floor_1", "bearing": -80.0, "distance": 12.0, "elevation": 0.0, "tags": []},
        {"id": "one_b", "object": None, "qualifier": None, "zone": "floor_1", "bearing": 150.0, "distance": 7.0, "elevation": 1.0, "tags": []},
        {"id": "two_a", "object": None, "qualifier": None, "zone": "floor_2", "bearing": 30.0, "distance": 14.0, "elevation": 3.2, "tags": []},
        {"id": "two_b", "object": None, "qualifier": None, "zone": "floor_2", "bearing": -120.0, "distance": 20.0, "elevation": 3.4, "tags": []},
        {"id": "roof_a", "object": None, "qualifier": None, "zone": "roof", "bearing": 0.0, "distance": 16.0, "elevation": 6.5, "tags": []},
        {"id": "door_one", "object": "door", "qualifier": None, "zone": "floor_1", "bearing": 40.0, "distance": 6.0, "elevation": 0.0, "tags": []},
        {"id": "door_two", "object": "door", "qualifier": None, "zone": "floor_2", "bearing": -30.0, "distance": 11.0, "elevation": 3.2, "tags": []},
        {"id": "stairs_red", "object": "stairs", "qualifier": "red", "zone": "floor_1", "bearing": 90.0, "distance": 10.0, "elevation": 0.0, "tags": []},
    ],
    "player_pin": None, "bot_pin": None, "player_gaze": None, "player": {"downed": False}, "bot": {"stance": "stand", "items": []},
}
DEV_FLOORS = [
    ("go upstairs", "MOVE_TO", {"action": "act", "zone": "up", "candidates": ["two_a", "two_b", "door_two"]}),       # the next floor up, not the roof
    ("go downstairs", "MOVE_TO", {"action": "act", "zone": "down", "candidates": ["base_a"]}),
    ("go to the second floor", "MOVE_TO", {"action": "act", "zone": "floor_2", "candidates": ["two_a", "two_b", "door_two"]}),
    ("get to the roof", "MOVE_TO", {"action": "act", "zone": "roof", "candidates": ["roof_a"]}),
    ("watch the door upstairs", "HOLD_ANGLE", {"action": "act", "entity": "door_two"}),                             # one door is above
    ("hold the door downstairs", "HOLD_ANGLE", {"action": "ask"}),                                                  # none below: "I see no door."
]


# a line of several orders, in the example world (two doors: 8 m ahead on the left, 11 m on the right). The third
# element: the line is a further order of the line before it (the decoder's order lines).
DEV_CHAIN = [
    ("smoke the door", "SMOKE", False, {"action": "ask"}),                                    # two doors: "Which door?"
    ("no", "NO", False, {"action": "ask"}),                                                   # not the one ahead
    ("yes", "YES", False, {"action": "resolved", "entity": "door_b"}),
    ("go in through the door", "MOVE_TO", True, {"action": "act", "entity": "door_b"}),       # the door that got the smoke
    ("hold the door", "HOLD_ANGLE", False, {"action": "ask"}),                                # a new line: asked again
    ("hold the other door", "HOLD_ANGLE", False, {"action": "resolved", "entity": "door_b"}),  # not the one just offered
    ("flash the door on the left", "FLASH", False, {"action": "act", "entity": "door_a"}),
    ("go in through the door", "MOVE_TO", True, {"action": "act", "entity": "door_a"}),       # fewer words, the same door
    ("check that window", "CHECK", True, {"action": "act", "entity": "win_a"}),               # another thing: grounded by itself
    ("frag the north door", "FRAG", False, {"action": "act", "entity": "door_a"}),
    ("hold the other door", "HOLD_ANGLE", True, {"action": "act", "entity": "door_b"}),       # "other" is not "the same"
    ("watch the door", "HOLD_ANGLE", True, {"action": "act", "entity": "door_b"}),            # the order before it, not the first
    ("watch the door", "HOLD_ANGLE", False, {"action": "ask"}),                               # the same words as a new line
    # "the other one" names no place; the classifier makes the other angle of it, nothing, or a no
    ("no, the other one", "HOLD_OTHER_ANGLE", False, {"action": "resolved", "entity": "door_b", "intent": "HOLD_ANGLE"}),
    ("breach the door", "BREACH", False, {"action": "ask"}),
    ("the other one", "NONE", False, {"action": "resolved", "entity": "door_b", "intent": "BREACH"}),
    ("open the door", "OPEN", False, {"action": "ask"}),
    ("no, the other one", "NO", False, {"action": "resolved", "entity": "door_b", "intent": "OPEN"}),
    ("hold the other angle", "HOLD_OTHER_ANGLE", False, {"action": "act", "intent": "HOLD_OTHER_ANGLE"}),   # nothing asked: the order
    # the decoder writes the answer out for every order of the line: the same words are the same door
    ("breach the door", "BREACH", False, {"action": "ask"}),
    ("breach the other door", "BREACH", False, {"action": "resolved", "entity": "door_b"}),
    ("frag the other door", "FRAG", True, {"action": "act", "entity": "door_b"}),             # not the other of the other
    ("go in through the door", "MOVE_TO", True, {"action": "act", "entity": "door_b"}),
]
# ... and on a map nobody has marked: the door is what the player points at when asked
DEV_CHAIN_BARE = [
    ("smoke the door", "SMOKE", False, {"action": "ask"}),                                    # "I see no door. Where?"
    ("there", "NONE", False, {"action": "resolved", "entity": "gaze_1"}),
    ("go in through the door", "MOVE_TO", True, {"action": "act", "entity": "gaze_1"}),       # the door pointed at
    ("frag the door", "FRAG", False, {"action": "ask"}),                                      # a new line: asked again
    ("at my pin", "NONE", False, {"action": "resolved", "entity": "pin"}),
    ("hold the door", "HOLD_ANGLE", True, {"action": "act", "entity": "pin"}),
    ("check the window", "CHECK", True, {"action": "ask"}),                                   # another thing: "I see no window."
]


def talk_change(pl, change):
    """Applies a DEV_TALK change to the planner's world; returns whether the line is to be under the threshold."""
    w = copy.deepcopy(pl.world)
    w["bot_pin"] = None      # the game sends its own; the planner's mark of where the bot goes is not an entity
    for key, value in change.items():
        if key == "gaze_enemy":
            w["entities"] = [e for e in w["entities"] if e["id"] != ENEMY["id"]] + [copy.deepcopy(ENEMY)]
            w["player_gaze"] = ENEMY["id"]
        elif key != "low":
            w[key] = copy.deepcopy(value)
    if "gaze_enemy" not in change:
        w["entities"] = [e for e in w["entities"] if e["id"] != ENEMY["id"]]
        w["player_gaze"] = "gaze_1"
    pl.set_world(w)
    return bool(change.get("low"))


def run_dev():
    os.environ.setdefault("COOP_TAG", "v54")
    import coop_bot
    labels = coop_bot.LINES.keys()

    class Fake:
        """A bot whose probabilities are given by name (no model): coop_bot.Bot.decide with its labels."""
        def __init__(self):
            self.labels = list(labels) + ["GO_NOW", "NONE"]
            from coop_v2 import FAMILY
            self.family = {k: FAMILY.get(k, k.lower()) for k in self.labels}
            self.phrase = {k: k.lower().replace("_", " ") for k in self.labels}
            self.gate, self.threshold = "top", 0.6
            self.reset()
        reset = coop_bot.Bot.reset
        pick = coop_bot.Bot.pick
        decide = coop_bot.Bot.decide

    ok = 0
    for world, dev in ((WORLD_EXAMPLE, DEV), (WORLD_BARE, DEV_BARE), (WORLD_TALK, DEV_TALK), (WORLD_FLOORS, DEV_FLOORS)):
        bot = Fake()
        pl = Planner(bot, world)
        for text, intent, want, *change in dev:
            low = False
            if change:
                low = talk_change(pl, change[0])
            probs = [0.0] * len(bot.labels)
            probs[bot.labels.index(intent)] = 0.45 if low else 0.9
            r = pl.step(text, probs)
            got = {"action": r["action"]}
            if r["order"]:
                got.update(entity=r["order"]["entity"], zone=r["order"]["zone"], via=r["order"]["via"], near=r["order"]["near"],
                           direction=r["order"]["direction"], intent=r["order"]["intent"], candidates=r["order"]["candidates"])
            good = all(got.get(k) == v for k, v in want.items())
            ok += good
            print(f"{'ok ' if good else 'NO '} {text!r:36s} -> {r['action']:9s} {r['say']}" + (f"  order {r['order']}" if r["order"] else ""))
    for world, dev in ((WORLD_EXAMPLE, DEV_CHAIN), (WORLD_BARE, DEV_CHAIN_BARE)):
        bot = Fake()
        pl = Planner(bot, world)
        for text, intent, continued, want in dev:
            probs = [0.0] * len(bot.labels)
            probs[bot.labels.index(intent)] = 0.9
            r = pl.step(text, probs, continued)
            got = {"action": r["action"]}
            if r["order"]:
                got.update(entity=r["order"]["entity"], intent=r["order"]["intent"])
            good = all(got.get(k) == v for k, v in want.items())
            ok += good
            print(f"{'ok ' if good else 'NO '} {('+ ' if continued else '') + repr(text):36s} -> {r['action']:9s} {r['say']}" + (f"  order {r['order']}" if r["order"] else ""))
    print(f"{ok}/{len(DEV) + len(DEV_BARE) + len(DEV_TALK) + len(DEV_FLOORS) + len(DEV_CHAIN) + len(DEV_CHAIN_BARE)}")


if __name__ == "__main__":
    run_dev()
