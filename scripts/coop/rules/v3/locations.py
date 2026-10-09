"""
Where the order points: the map's named places (locations.json) found in a transcript.

The classifier picks the intent; this finds the places the planner resolves on the map:
    "hold the north door in the basement"            -> door / north / basement
    "i'll take the north door, you take the south"   -> door north (role mine), then door south: primary
    "take blue"                                      -> stairs / blue (inferred: only stairs are blue)
    "two on red stairs, hold the main door"          -> stairs red (role them), door main: primary
    "get to the roof"                                -> zone roof
It is a dictionary and position rules, not a model: the vocabulary is closed and the same on every
map, and a new callout must work the moment it is added to locations.json.

Everything is defined on the UTF-8 bytes of the line, so the C++ port is the same loop: a token is a
maximal run of ASCII letters and digits (A-Z lowercased), every other byte separates; between two
tokens a comma is a weak break (1) and . ; : ! ? a strong one (2). Offsets are byte offsets. Filler
words ("uh", "um") are dropped, and only the last MAX_TOKENS tokens are read (an order ends a ramble).

Rule sets (the word lists are in locations.json "words"):
  v1  frozen before any v3 test line existed (rules/v1): the only set with a blind number on the first
      v3 lines (88.0% exact).
  v2  after that run, from the r6 and cs authors' lines (rules/v2).
  v3  this file, after the review of v2: roles no longer fire on ordinary orders, "on second" is a
      floor only where it ends its phrase, zones and loose names do not attach across a clause, the
      unknown_modifier flag looks after the object too. Written after the first v3 lines had been
      seen; its blind number is on the second batch (blind/v3b, eval_v3b.py).

  mentions    left to right, the longest vocabulary phrase at each token: object, qualifier, named
              place (object + qualifier in one phrase), zone, or an "ignore" phrase ("off the table").
              A zone's "words_end" phrase ("on second") counts only where it ends its phrase: at the
              end of the line, before punctuation or before a lone_follow word.
  before      an object takes the qualifier standing right before it (nothing, or one before_fill
              word, between; no punctuation). "north and south doors" makes two targets.
  other       an unqualified object right after an `other` word is flagged "other" ("take the other
              door"): the other one of its kind.
  unknown     the target is flagged "unknown_modifier" -- the player singled out one object in a way
              the map names cannot express, and the planner must not fall back to the nearest one --
              when: the object cannot carry the qualifier ("blue door"); two qualifiers stand side by
              side ("north west door"); an unknown_modifier word stands right before it ("back door",
              "first door"); exactly one word the vocabulary does not know stands between a determiner
              and an unqualified object ("the spiral staircase"; not a preposition, a number or an
              order verb: "a flash through window" is not flagged); or a post_prep word, an optional
              determiner and a post_modifier word follow an unqualified object ("the door on the
              left").
  after       a qualifier still free attaches to the object before it when only after_fill words
              (at most 4, zone phrases skipped) stand between, without punctuation: "door on the north
              side". Across a comma only when a tail word follows it ("the stairs, blue ones"). A
              qualifier followed by a lone_block word or a zone phrase belongs to that phrase ("the
              door to the main hall"). If the object already has a qualifier, it is a second target
              of the same kind ("not the north door, the south one").
  lone        a qualifier no object took is a place only where it ends its phrase: at the end of the
              line, before punctuation, before a lone_follow word, or before a word that starts
              the next clause (a subject, a negator, a determiner, a number, an order verb: "take
              blue ill take red"). Before a lone_block word or a zone phrase ("yellow ping", "main
              hall") and after a lone_not_after word ("i'm red") it is nothing; before any other word
              it is a target flagged "unsure". Its object is the qualifier's "lone" object (blue ->
              stairs, main -> door); a compass word has none, so the target has only a qualifier (a
              direction) -- unless it points back at an object named before: "you take the south
              one", "i'll watch the east window, you watch the west" -> that kind of object.
  zone        a zone belongs to a target only inside its noun phrase: right before it ("basement
              door") or after it with only zone_after_fill words (at most 3) between, without
              punctuation. Across a comma only as shorthand, the zone an item of its own: "first
              floor, north window", "basement, the east door", "red stairs, top floor, two of them";
              not "get to the basement, the door is open". Any other zone is a target of its own.
  role        whose place it is. A place joined to the one before it by and / or shares its role
              ("they're on red and blue"). Else, looking back at most 5 words from a target
              (auxiliaries, determiners and particles not counted), not across punctuation, "you" or
              another target, and not past an order verb that starts the bot's own order
              ("im planting watch the white stairs"; a verb with its subject or negator right before
              it -- "i'll take", "i'm going to breach", "don't open", "they hold" -- hands the search
              to that subject or negator):
                not     a role_not word ("don't forget to", "don't let", "do not lose" excepted)
              (from / off / out of / leave count only right before the place, "back off to the
              basement" is a destination; and not after a negator: "dont leave the red stairs")
                from    leave / leaving; "from" or "off" after a from_lead word ("fall back from",
                        "get off") or when "to <another place>" follows ("from blue to red",
                        "from the roof rappel down to the east window"); "out of".
                        "cover me from the east window", "smoke off the main door": no role
                mine    i / i'm / i'll / i've, unless a report verb follows ("i said", "i need") or
                        it is a request ("can i get smoke on ..."); an -ing word that starts the
                        line or the clause ("pushing main", "i'm hit, falling back to the basement")
                them    a role_them word ("they", "enemy", "footsteps"). A role_them_soft word
                        ("guy", "someone", "stack") or a number, when what follows is what an enemy
                        does there: a form of "be", an -ing word or a motion_past word ("stack is
                        sitting on ...", "someone just ran up ...", "two of them pushing ..."), or a
                        number_next word where a callout starts -- the line or clause start, after
                        a lead word or after another place ("two on red", "got one at ...", "i hear
                        someone in ..."). "put one on the north door", "stack up on the north
                        door", "you guys on the main door", "no contact at ..." get no role.
                        "taking fire from the roof" is the enemy's place too
              "status" (a status_next word follows the target, and not "is yours" / "is all you") is
              given only when the line has another place to act on, or asks for "the other one":
              "north door is clear, hold the south window"; "east door's barricaded, blow it" has none.
  primary     the first target without a role. If every target has one, the first target: then the
              line gives no destination, and the role says why ("get off the roof": the place to
              leave).

normalized(text, "strip") is the line with attached qualifiers removed ("hold the north door" ->
"hold the door"), for measuring whether the classifier does better on it (eval_v3.py). Lone
qualifiers and zones are left alone: replacing them changed the meaning of orders ("push main" ->
"push the door" reads as OPEN; "go to the roof" -> "go to there" loses RAPPEL).

    python locations.py "hold the north door in the basement"
    python locations.py --dev          # the developer's regression lines (locations_dev.json)
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE_WINDOW = 5
ROLE_REACH = 12
ANAPHOR_MAX = 6
AFTER_MAX = 4
ZONE_AFTER_MAX = 3
GOVERN_MAX = 4
MAX_PHRASE_TOKENS = 4
MAX_TOKENS = 128
SECTIONS = ("version", "objects", "qualifiers", "named", "zones", "ignore", "words")
WORD_LISTS = ("before_fill", "after_fill", "tail", "zone_after_fill", "lone_follow",
              "lone_block", "lone_not_after", "unknown_modifier", "role_not", "role_from", "role_mine",
              "role_them", "number", "number_next", "status_next", "role_stop", "report_verb", "other",
              "determiner", "neutral_modifier",
              "role_them_soft", "soft_fill", "soft_lead", "number_fill", "motion_past", "role_from_of", "of_lead", "be", "not_ing", "role_from_after", "from_lead", "from_to", "ask", "number_lead",
              "status_not_next", "not_exempt", "not_unless_to", "govern", "aux", "order_verb", "from_particle",
              "filler", "anaphor", "let", "let_me", "negator", "fire", "no_words",
              "preposition", "post_prep", "post_modifier")


def _is_token_byte(c):
    return 97 <= c <= 122 or 48 <= c <= 57


def tokenize(text):
    """[(word, start, end, brk)] over the UTF-8 bytes; brk is the punctuation between the previous
    token and this one: 0 none, 1 comma, 2 a sentence break (. ; : ! ?)."""
    b = text.encode("utf-8") if isinstance(text, str) else text
    out, i, n, brk = [], 0, len(b), 0
    while i < n:
        c = b[i] + 32 if 65 <= b[i] <= 90 else b[i]
        if _is_token_byte(c):
            j, word = i, []
            while j < n:
                d = b[j] + 32 if 65 <= b[j] <= 90 else b[j]
                if not _is_token_byte(d):
                    break
                word.append(d)
                j += 1
            out.append((bytes(word).decode("ascii"), i, j, brk if out else 0))
            i, brk = j, 0
        else:
            if c in b".;:!?":
                brk = 2
            elif c == 44 and brk < 2:
                brk = 1
            i += 1
    return out


def _phrase_ok(p):
    parts = p.split(" ")
    return bool(p) and all(x and all(_is_token_byte(ord(ch)) for ch in x) for x in parts) and len(parts) <= MAX_PHRASE_TOKENS


def validate(v):
    """Every reason this vocabulary must not be loaded (an empty list: it is fine)."""
    errs = []
    for k in v:
        if k not in SECTIONS and not k.startswith("_"):
            errs.append(f"unknown section {k!r}")
    for k in SECTIONS:
        if k not in v:
            errs.append(f"missing section {k!r}")
    if errs:
        return errs
    owner = {}

    def claim(phrase, who):
        if not isinstance(phrase, str) or not _phrase_ok(phrase):
            errs.append(f"{who}: phrase {phrase!r} must be 1-{MAX_PHRASE_TOKENS} lowercase ASCII tokens separated by single spaces")
        elif phrase in owner:
            errs.append(f"phrase {phrase!r} is in both {owner[phrase]} and {who}")
        else:
            owner[phrase] = who

    obj_ids, qual_ids = [o.get("id") for o in v["objects"]], [q.get("id") for q in v["qualifiers"]]
    for ids, what in ((obj_ids, "object"), (qual_ids, "qualifier"), ([z.get("id") for z in v["zones"]], "zone")):
        for i in set(ids):
            if ids.count(i) > 1:
                errs.append(f"duplicate {what} id {i!r}")
    allowed = {}
    for o in v["objects"]:
        if not o.get("words"):
            errs.append(f"object {o.get('id')!r} has no words")
        for w in o.get("words", []):
            claim(w, f"object {o.get('id')}")
        for q in o.get("qualifiers", []):
            if q not in qual_ids:
                errs.append(f"object {o.get('id')!r} allows unknown qualifier {q!r}")
        allowed[o.get("id")] = set(o.get("qualifiers", []))
    for q in v["qualifiers"]:
        for w in q.get("words", []):
            claim(w, f"qualifier {q.get('id')}")
        if not any(q.get("id") in a for a in allowed.values()):
            errs.append(f"qualifier {q.get('id')!r} is allowed by no object")
        if "lone" not in q:
            errs.append(f"qualifier {q.get('id')!r} needs an explicit \"lone\" (an object id or null)")
        elif q["lone"] is not None and q.get("id") not in allowed.get(q["lone"], ()):
            errs.append(f"qualifier {q.get('id')!r}: lone object {q['lone']!r} does not allow it")
    for t in v["named"]:
        claim(t.get("phrase"), "named")
        if t.get("qualifier") not in allowed.get(t.get("object"), ()):
            errs.append(f"named {t.get('phrase')!r}: {t.get('object')!r} does not allow {t.get('qualifier')!r}")
    for z in v["zones"]:
        if not z.get("words"):
            errs.append(f"zone {z.get('id')!r} has no words")
        for w in z.get("words", []):
            claim(w, f"zone {z.get('id')}")
        for w in z.get("words_end", []):
            claim(w, f"zone {z.get('id')} (words_end)")
    for p in v["ignore"]:
        claim(p, "ignore")
    for k in WORD_LISTS:
        if k not in v["words"]:
            errs.append(f"missing word list {k!r}")
    for k, ws in v["words"].items():
        if k not in WORD_LISTS:
            errs.append(f"unknown word list {k!r}")
        for w in ws:
            if not _phrase_ok(w) or " " in w:
                errs.append(f"word list {k}: {w!r} must be one lowercase ASCII token")
    return errs


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    for k in set(keys):
        if keys.count(k) > 1:
            raise ValueError(f"duplicate key {k!r} in the vocabulary file")
    return dict(pairs)


def load_vocab(path=None):
    v = json.load(io.open(path or os.path.join(HERE, "locations.json"), encoding="utf-8"),
                  object_pairs_hook=_no_duplicate_keys)
    errs = validate(v)
    if errs:
        raise ValueError("locations vocabulary refused:\n  " + "\n  ".join(errs))
    phrases = {}
    for o in v["objects"]:
        for w in o["words"]:
            phrases[tuple(w.split(" "))] = ("object", o["id"])
    for q in v["qualifiers"]:
        for w in q["words"]:
            phrases[tuple(w.split(" "))] = ("qualifier", q["id"])
    for t in v["named"]:
        phrases[tuple(t["phrase"].split(" "))] = ("named", (t["object"], t["qualifier"]))
    for z in v["zones"]:
        for w in z["words"]:
            phrases[tuple(w.split(" "))] = ("zone", z["id"])
        for w in z.get("words_end", []):
            phrases[tuple(w.split(" "))] = ("zone_end", z["id"])
    for p in v["ignore"]:
        phrases[tuple(p.split(" "))] = ("ignore", None)
    return {"phrases": phrases, "max_len": max(map(len, phrases)),
            "allowed": {o["id"]: set(o["qualifiers"]) for o in v["objects"]},
            "lone": {q["id"]: q["lone"] for q in v["qualifiers"]},
            "w": {k: set(ws) for k, ws in v["words"].items()}, "version": v["version"]}


VOCAB = load_vocab()


def _target(obj, qual, first, last, source, **more):
    t = {"object": obj, "qualifier": qual, "zone": None, "role": None, "flag": None, "inferred": False,
         "first": first, "last": last, "obj": source, "cut": []}
    t.update(more)
    return t


def find(text, vocab=VOCAB):
    """-> {"targets": [...in line order...], "primary": index or -1, "target": the primary's
    {object, qualifier, zone, role, flag} or None}. Token positions: "first" / "last"."""
    W = vocab["w"]
    toks, carry = [], 0
    for w, a, b, br in tokenize(text):
        if w in W["filler"]:              # "hold the north uh door": the recogniser's fillers are not words of the line
            carry = max(carry, br)
            continue
        toks.append((w, a, b, max(carry, br) if toks else 0))
        carry = 0
    toks = toks[-MAX_TOKENS:]             # the last ones: an order ends a ramble
    if toks:
        toks[0] = toks[0][:3] + (0,)
    words = [t[0] for t in toks]
    n = len(toks)

    def ends_phrase(j):      # token j does not continue the phrase before it
        return j >= n or toks[j][3] or words[j] in W["lone_follow"]

    mentions, i = [], 0
    while i < n:
        for k in range(min(vocab["max_len"], n - i), 0, -1):
            hit = vocab["phrases"].get(tuple(words[i:i + k]))
            # a phrase does not run across punctuation ("first, floor")
            if hit and not any(toks[j][3] for j in range(i + 1, i + k)):
                if hit[0] == "zone_end":
                    if not ends_phrase(i + k):
                        continue               # "on second thought", "to second door"
                    hit = ("zone", hit[1])
                if hit[0] != "ignore":
                    mentions.append({"kind": hit[0], "value": hit[1], "first": i, "last": i + k - 1,
                                     "start": toks[i][1], "end": toks[i + k - 1][2]})
                i += k
                break
        else:
            i += 1
    kind_at = {j: m["kind"] for m in mentions for j in range(m["first"], m["last"] + 1)}

    def brk(a, b):          # the strongest punctuation between token a and token b (a < b)
        return max((toks[j][3] for j in range(a + 1, b + 1)), default=0)

    def gap(a, b, skip=()):  # the words strictly between tokens a and b, without mentions of the kinds in skip
        return [words[j] for j in range(a + 1, b) if kind_at.get(j) not in skip]

    objects = [m for m in mentions if m["kind"] in ("object", "named")]
    quals = [m for m in mentions if m["kind"] == "qualifier"]
    zones = [m for m in mentions if m["kind"] == "zone"]
    targets = []
    for o in objects:
        obj, q = (o["value"], None) if o["kind"] == "object" else o["value"]
        targets.append(_target(obj, q, o["first"], o["last"], o))
    by_obj = {id(t["obj"]): t for t in targets}
    free = [True] * len(quals)

    # 1. the qualifier right before its object
    for t in list(targets):
        o = t["obj"]
        if t["qualifier"] is not None:
            continue
        best = None
        for k, q in enumerate(quals):
            if not free[k] or q["last"] >= o["first"]:
                continue
            g = gap(q["last"], o["first"])
            if len(g) <= 1 and set(g) <= W["before_fill"] and not brk(q["last"], o["first"]):
                if best is None or q["last"] > quals[best]["last"]:
                    best = k
        if best is None:
            continue
        q = quals[best]
        free[best] = False
        if q["value"] not in vocab["allowed"][t["object"]]:      # "blue door": not a place on these maps
            t["flag"], t["first"] = "unknown_modifier", q["first"]
            continue
        t["qualifier"], t["first"] = q["value"], q["first"]
        t["cut"].append((q["start"], o["start"]))
        # 1b. "north and south doors" (two targets) / "north west door" (not a place)
        for k2, q1 in enumerate(quals):
            if free[k2] and q1["last"] < q["first"] and q1["value"] in vocab["allowed"][t["object"]]:
                g = gap(q1["last"], q["first"])
                if g in (["and"], ["or"]) or (not g and brk(q1["last"], q["first"]) == 1):
                    free[k2] = False
                    targets.append(_target(t["object"], q1["value"], q1["first"], q1["last"], o, twin=t,
                                           cut=[(q1["start"], q["start"])]))
                elif not g and not brk(q1["last"], q["first"]):
                    free[k2] = False
                    t["flag"], t["first"] = "unknown_modifier", q1["first"]
    # 1c. a modifier word the vocabulary does not have, right before the object: "back door"
    for t in targets:
        if "twin" not in t and t["first"] > 0 and words[t["first"] - 1] in W["unknown_modifier"] \
                and not toks[t["first"]][3] and kind_at.get(t["first"] - 1) is None:
            t["flag"] = "unknown_modifier"

    # 1d. "the spiral staircase", "that broken window": one word the vocabulary does not know between
    # a determiner and an unqualified object singles out one object
    for t in targets:
        f = t["first"]
        if "twin" in t or t["flag"] or t["qualifier"] is not None or f < 2:
            continue
        w = words[f - 1]
        if words[f - 2] in W["determiner"] and not toks[f - 1][3] and not toks[f][3] and kind_at.get(f - 1) is None \
                and not any(w in W[k] for k in ("neutral_modifier", "determiner", "preposition", "number", "order_verb")):
            t["flag"] = "unknown_modifier"

    # 1e. "take the other door": the object right after an `other` word is the other one of its kind
    for t in targets:
        f = t["first"]
        if "twin" not in t and t["flag"] is None and t["qualifier"] is None and f > 0 and not toks[f][3] \
                and words[f - 1] in W["other"]:
            t["flag"] = "other"

    # 2. a free qualifier after an object
    for k, q in enumerate(quals):
        if not free[k]:
            continue
        prev = [o for o in objects if o["last"] < q["first"]]
        if not prev:
            continue
        o = prev[-1]
        t = by_obj[id(o)]
        nxt = q["last"] + 1
        if nxt < n and not toks[nxt][3] and (words[nxt] in W["lone_block"] or kind_at.get(nxt) == "zone"):
            continue                       # "the door to the main hall": the name belongs to that phrase
        tail = nxt < n and words[nxt] in W["tail"] and not toks[nxt][3]
        b = brk(o["last"], q["first"])
        g = gap(o["last"], q["first"], skip=("zone",))
        if (q["value"] in vocab["allowed"][t["object"]] and len(g) <= AFTER_MAX and set(g) <= W["after_fill"]
                and (b == 0 or (b == 1 and tail))
                and not any(kind_at.get(j) == "qualifier" for j in range(o["last"] + 1, q["first"]))):
            free[k] = False
            last = q["last"] + (1 if tail else 0)
            zs = [z for z in zones if o["last"] < z["first"] < q["first"]]
            if t["qualifier"] is None:
                t["qualifier"], t["last"], t["after"] = q["value"], last, True
                t["cut"].append((zs[-1]["end"] if zs else o["end"], toks[last][2]))
            else:                          # "not the north door, the south one": a second door
                targets.append(_target(t["object"], q["value"], q["first"], last, o))
    # 2b. "doors and windows on the north side": coordinated objects share the qualifier after them
    for a, b in zip(objects, objects[1:]):
        ta, tb = by_obj[id(a)], by_obj[id(b)]
        if gap(a["last"], b["first"]) in (["and"], ["or"]) and ta["flag"] is None:
            ta["shares"] = tb
            if ta["qualifier"] is None and tb.get("after") and tb["qualifier"] in vocab["allowed"][ta["object"]]:
                ta["qualifier"] = tb["qualifier"]
    # 2c. "the door on the left", "the stairs at the back": a modifier after an unqualified object
    for o in objects:
        t = by_obj[id(o)]
        e = o["last"] + 1
        if t["flag"] or t["qualifier"] is not None or e >= n or toks[e][3] or words[e] not in W["post_prep"]:
            continue
        e += 1
        if e < n and not toks[e][3] and words[e] in W["determiner"]:
            e += 1
        if e < n and not toks[e][3] and words[e] in W["post_modifier"] and kind_at.get(e) is None:
            t["flag"] = "unknown_modifier"

    # 3. lone qualifiers: a place only where the word ends its phrase
    for k, q in enumerate(quals):
        if not free[k]:
            continue
        if q["first"] > 0 and not toks[q["first"]][3] and words[q["first"] - 1] in W["lone_not_after"]:
            continue                       # "i'm red"
        nxt = q["last"] + 1
        flag = None
        if not ends_phrase(nxt):
            if words[nxt] in W["lone_block"] or kind_at.get(nxt) == "zone":
                continue                   # "yellow ping", "main hall"
            # a word that starts the next clause ends the phrase too: "take blue ill take red"
            if not any(words[nxt] in W[k] for k in ("role_mine", "role_not", "role_them", "govern", "determiner",
                                                    "number", "order_verb")):
                flag = "unsure"            # "the white fence": maybe a phrase the vocabulary does not know
        obj = vocab["lone"][q["value"]]
        # "you take the south one", "i'll watch the east window, you watch the west": the kind of the
        # object named before
        prev = [o for o in objects if o["last"] < q["first"] and q["value"] in vocab["allowed"][by_obj[id(o)]["object"]]]
        if prev:
            pt = by_obj[id(prev[-1])]
            one = nxt < n and not toks[nxt][3] and words[nxt] in W["anaphor"]
            bare = (obj is None and flag is None and ends_phrase(nxt) and q["first"] > 0
                    and words[q["first"] - 1] in W["determiner"] and not toks[q["first"]][3]
                    and pt["qualifier"] not in (None, q["value"]) and q["first"] - prev[-1]["last"] <= ANAPHOR_MAX)
            if one or bare:
                obj = pt["object"]
        last = q["last"] + (1 if nxt < n and words[nxt] in W["tail"] and not toks[nxt][3] else 0)
        targets.append(_target(obj, q["value"], q["first"], last, None, flag=flag, inferred=obj is not None))
    targets.sort(key=lambda t: t["first"])

    # 4. zones
    placed = []
    for z in zones:
        best = None
        for t in targets:
            if "zone_at" in t:
                continue
            if z["last"] < t["first"]:
                # "basement door"; across a comma only as shorthand, the zone an item of its own:
                # "first floor, north window", "basement, the east door, smoke it"
                g, b = gap(z["last"], t["first"]), brk(z["last"], t["first"])
                if (not g and not b) or (b == 1 and toks[z["last"] + 1][3] == 1 and (z["first"] == 0 or toks[z["first"]][3])
                                         and (not g or (len(g) == 1 and g[0] in W["determiner"]))):
                    best = best or t
            elif z["first"] > t["last"] or (t["obj"] is not None and t["obj"]["last"] < z["first"] <= t["last"]):
                a = t["obj"]["last"] if t["obj"] is not None and z["first"] <= t["last"] else t["last"]
                g = gap(a, z["first"])
                b = brk(a, z["first"])
                # across a comma only as shorthand, the zone an item of its own: "red stairs, top floor, ..."
                if (len(g) <= ZONE_AFTER_MAX and set(g) <= W["zone_after_fill"]
                        and (b == 0 or (b == 1 and not g and (z["last"] + 1 >= n or toks[z["last"] + 1][3])))
                        and not any(a < u["first"] < z["first"] for u in targets if u is not t)):
                    best = t
                    t["zone_after"] = True
        if best is not None:
            best["zone"], best["zone_at"] = z["value"], z["first"]
            placed.append(z)
    for t in targets:
        if t.get("shares") is not None and t["zone"] is None and t["shares"].get("zone_after"):
            t["zone"] = t["shares"]["zone"]
        if t.get("twin") is not None and t["zone"] is None:
            t["zone"] = t["twin"]["zone"]
    for z in zones:
        if z not in placed:
            targets.append(_target(None, None, z["first"], z["last"], None, zone=z["value"]))
    targets.sort(key=lambda t: t["first"])

    # 5. roles: whose place it is
    owned = set()
    for t in targets:
        owned.update(range(t["first"], t["last"] + 1))

    def let_me(k):           # "let me take the north door": "me" is the subject
        return words[k] in W["let_me"] and k > 0 and not toks[k][3] and words[k - 1] in W["let"]

    def governor(j):         # the subject or negator right before the order verb at j (auxiliaries between), or -1
        k = j - 1
        for _ in range(GOVERN_MAX + 1):
            if k < 0 or toks[k + 1][3]:
                return -1
            if words[k] in W["role_not"] or words[k] in W["role_mine"] or words[k] in W["govern"] or let_me(k):
                return k
            if words[k] not in W["aux"]:
                return -1
            k -= 1
        return -1

    def ing(j):              # "camping", "sitting": a progressive form (by its ending; not_ing: "thing", "building")
        return j < n and len(words[j]) > 4 and words[j].endswith("ing") and words[j] not in W["not_ing"]

    def after(j, fill):      # the token after j and at most two filler words: "two of them | on", "guy just | went"
        k = j + 1
        for _ in range(2):
            if k < n and not toks[k][3] and words[k] in W[fill]:
                k += 1
        return k

    def acts(k):             # what an enemy does there: "is", "sitting", "went"
        return k < n and not toks[k][3] and (words[k] in W["be"] or ing(k) or words[k] in W["motion_past"])

    def starts(j, more=()):  # token j starts a callout: line or clause start, after a lead word or after another place
        return j == 0 or toks[j][3] or words[j - 1] in W["number_lead"] or j - 1 in owned or any(words[j - 1] in W[m] for m in more)

    def leads_to(t):         # "from blue to red", "from the roof rappel down to the east window"
        e = t["last"] + 1
        for skip in ("order_verb", "from_particle"):
            if e < n and not toks[e][3] and words[e] in W[skip] and kind_at.get(e) is None:
                e += 1
        if e >= n or toks[e][3] or words[e] not in W["from_to"]:
            return False
        e += 1
        if e < n and not toks[e][3] and words[e] in W["determiner"]:
            e += 1
        return e < n and not toks[e][3] and kind_at.get(e) is not None

    def negated(j):          # a negator right before token j: "dont leave", "don't move from"
        k = j - 2 if j >= 2 and words[j - 1] == "t" else j - 1
        return k >= 0 and not toks[j][3] and words[k] in W["negator"]

    def next_to(j, t):       # only determiners and neutral words between token j and the place
        return all(words[x] in W["determiner"] or words[x] in W["neutral_modifier"] for x in range(j + 1, t["first"]))

    for ti, t in enumerate(targets):
        # "they're on red and blue": a place joined to the one before it by and / or shares its role
        if ti and targets[ti - 1]["role"] in ("mine", "them", "not"):
            u = targets[ti - 1]
            g = [words[x] for x in range(u["last"] + 1, t["first"])]
            if g and brk(u["last"], t["first"]) < 2 and any(x in ("and", "or") for x in g) \
                    and all(x in ("and", "or") or x in W["determiner"] for x in g):
                t["role"] = u["role"]
                continue
        j, steps = t["first"] - 1, 0
        while j >= 0 and steps < ROLE_WINDOW and t["first"] - j <= ROLE_REACH:
            if toks[j + 1][3] or words[j] in W["role_stop"] or j in owned:
                break
            w = words[j]
            soft = False
            if w in W["role_them_soft"]:   # "stack is sitting on ...", "guy on ..."; not "stack up on the north door"
                k = after(j, "soft_fill")
                soft = k < t["first"] and (acts(k) or (words[k] in W["number_next"] and w not in W["order_verb"]
                                                       and starts(j, ("soft_lead", "number"))))
            # an order verb starts the bot's own order, unless it is a noun here ("a smoke", "the drone")
            if w in W["order_verb"] and not soft and not (j > 0 and not toks[j][3] and words[j - 1] in W["determiner"]):
                j = governor(j)
                if j < 0:
                    break                  # "im planting watch the white stairs": the bot's own order starts here
                w = words[j]               # "i'm going to breach the north door": straight to the subject
            if w in W["role_not"]:
                k = j + 2 if words[j + 1] == "t" else j + 1     # "don't" is two tokens
                if (w in W["not_unless_to"] and words[j + 1] == "to") or (k < n and words[k] in W["not_exempt"]):
                    break                  # "don't forget to smoke the north door", "do not lose the top floor"
                t["role"] = "not"
            elif w in W["role_from"]:
                if negated(j):
                    break                  # "dont leave the red stairs": stay there
                if next_to(j, t):
                    t["role"] = "from"
            elif w in W["role_from_after"]:
                lead = j - 2 if j >= 2 and not toks[j][3] and words[j - 1] in W["from_particle"] else j - 1
                if j > 0 and not toks[j][3] and words[j - 1] in W["fire"]:
                    t["role"] = "them"     # "taking fire from the roof"
                elif lead >= 0 and not toks[lead + 1][3] and words[lead] in W["from_lead"] and next_to(j, t):
                    if negated(lead):
                        break              # "don't move from the north window"
                    t["role"] = "from"     # "fall back from", "come down from"; not "back off to the basement"
                elif leads_to(t):
                    t["role"] = "from"     # else the bot's own position: "cover me from the east window"
            elif w in W["role_mine"] or let_me(j):
                k = j + 1
                while k < t["first"] and words[k] in W["aux"]:
                    k += 1
                if words[k] in W["report_verb"] or (j > 0 and not toks[j][3] and words[j - 1] in W["ask"]):
                    break                  # "I said the west door", "can i get smoke on the north door"
                t["role"] = "mine"
            elif w in W["role_from_of"]:
                if j > 0 and not toks[j][3] and words[j - 1] in W["of_lead"] and next_to(j, t):
                    t["role"] = "from"     # "get out of the basement"
            elif w in W["role_them"] or soft:
                if j > 0 and not toks[j][3] and words[j - 1] in W["no_words"]:
                    break                  # "no contact at the north door"
                t["role"] = "them"
            elif w in W["number"]:
                k = after(j, "number_fill")
                if k < t["first"] and (words[k] in W["number_next"] or acts(k)) and starts(j):
                    t["role"] = "them"     # "two on red", "got one at main"; not "put one on the north door"
            elif ing(j) and (j == 0 or toks[j][3]):
                t["role"] = "mine"         # "pushing main", "i'm hit, falling back to the basement": a report, not an order
            if t["role"]:
                break
            # auxiliaries, determiners and particles do not use up the window: "i'm falling back to the main door"
            steps += 0 if any(w in W[k] for k in ("aux", "determiner", "from_particle")) else 1
            j -= 1

    # 5a. status: "north door is clear, hold the south window". Only when the line has another place to
    # act on (or asks for "the other one"): "east door's barricaded, blow it" names its own target
    def status_follows(t):
        e = t["last"] + 1
        if e >= n or toks[e][3] or words[e] not in W["status_next"]:
            return False
        return not (e + 1 < n and not toks[e + 1][3] and words[e + 1] in W["status_not_next"])

    def other_after(a):      # "... take the other one", "... you take the other"; not "on the other side"
        return any(words[j] in W["other"] and (j + 1 >= n or toks[j + 1][3] or words[j + 1] in W["anaphor"])
                   for j in range(a, n))

    cand = [t for t in targets if t["role"] is None and status_follows(t)]
    if cand and (any(t["role"] is None and not any(t is c for c in cand) for t in targets)
                 or other_after(targets[-1]["last"] + 1)):
        for t in cand:
            t["role"] = "status"

    # 5b. a correction reaches back: "smoke blue stairs, no wait, not blue, I meant white"
    for k, t in enumerate(targets):
        if t["role"] == "not" and t["qualifier"] is not None:
            for u in targets[:k]:
                if u["role"] is None and u["qualifier"] == t["qualifier"] and u["object"] in (t["object"], None):
                    u["role"] = "not"
    # 5c. "I've got the north door, you take the other one", "not the north door, the other one": no
    # named place is the bot's, and the line asks for the other one -> another object of that kind
    if targets and all(t["role"] for t in targets):
        t = targets[-1]
        if t["object"] is not None and other_after(t["last"] + 1):
            targets.append(_target(t["object"], None, n, n, None, flag="other"))

    primary = next((k for k, t in enumerate(targets) if t["role"] is None), 0 if targets else -1)
    keys = ("object", "qualifier", "zone", "role", "flag")
    return {"targets": targets, "primary": primary,
            "target": {k: targets[primary][k] for k in keys} if primary >= 0 else None}


def record(text, vocab=VOCAB):
    """What the bot hands the planner: the targets in line order and which one is primary."""
    r = find(text, vocab)
    keys = ("object", "qualifier", "zone", "role", "flag", "inferred")
    return {"primary": r["primary"], "targets": [{k: t[k] for k in keys} for t in r["targets"]]}


def normalized(text, mode, vocab=VOCAB):
    """mode "raw": the line itself. "strip": attached qualifiers removed; a line with nothing to
    remove comes back byte for byte."""
    if mode == "raw":
        return text
    assert mode == "strip", mode
    b = text.encode("utf-8")
    cuts = sorted(c for t in find(text, vocab)["targets"] for c in t["cut"])
    if not cuts:
        return text
    out, pos = bytearray(), 0
    for s, e in cuts:
        if s < pos:
            continue
        out += b[pos:s]
        pos = e
    out += b[pos:]
    res = bytearray()
    for c in out:                          # one space where a cut left two, none before a comma or at the ends
        if c == 32 and (not res or res[-1] == 32):
            continue
        if c == 44 and res and res[-1] == 32:
            res.pop()
        res.append(c)
    while res and res[-1] == 32:
        res.pop()
    return res.decode("utf-8")


def run_dev(path=None, show=True):
    """The developer's regression lines: {cat, text, accept: [[object, qualifier, zone] | null |
    "FLAG" | "ROLE"]}; a case may also fix the primary's "role" and "flag" (null: none). Tuning
    material, never a test set."""
    cases = json.load(io.open(path or os.path.join(HERE, "locations_dev.json"), encoding="utf-8"))["cases"]
    fails = {}
    for c in cases:
        t = find(c["text"])["target"]
        got = None if t is None else [t["object"], t["qualifier"], t["zone"]]
        ok = got in [a for a in c["accept"] if not isinstance(a, str)] or \
            ("FLAG" in c["accept"] and t and t["flag"]) or ("ROLE" in c["accept"] and t and t["role"])
        for k in ("role", "flag"):
            if k in c and (t[k] if t else None) != c[k]:
                ok = False
        if not ok:
            fails.setdefault(c["cat"], []).append((c["text"], got, t and t["role"], t and t["flag"], c))
    n_fail = sum(map(len, fails.values()))
    if show:
        print(f"{len(cases)} dev lines, {n_fail} with a primary target the line's author would not accept")
        for cat, rows in fails.items():
            for text, got, role, flag, c in rows:
                want = f"{c['accept']}" + "".join(f" {k}={c[k]}" for k in ("role", "flag") if k in c)
                print(f"  [{cat}] {text!r}: got {got} role={role} flag={flag}, want {want}")
    return n_fail


if __name__ == "__main__":
    if "--dev" in sys.argv:
        sys.exit(1 if run_dev() else 0)
    for line in sys.argv[1:]:
        print(json.dumps({"text": line, **record(line), "strip": normalized(line, "strip")}))
