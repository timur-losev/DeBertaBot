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
tokens a comma is a weak break (1) and . ; : ! ? a strong one (2). Offsets are byte offsets.

Rules (v1 was frozen before any v3 test line existed; v2 added 1d, 5b, 5c and the report verbs after
the first blind run, from the r6 and cs authors' lines only -- eval_v3.py reports the stt author
separately; the word lists are in locations.json "words")
  mentions    left to right, the longest vocabulary phrase at each token: object, qualifier, named
              place (object + qualifier in one phrase), zone, or an "ignore" phrase ("two steps").
  before      an object takes the qualifier standing right before it (nothing, or one before_fill
              word, between; no punctuation). A qualifier the object cannot carry ("blue door"), two
              qualifiers side by side ("north west door") or an unknown_modifier word ("back door")
              flag the target "unknown_modifier": the planner must not fall back to the nearest one.
              "north and south doors" makes two targets.
  after       a qualifier still free attaches to the object before it when only after_fill words
              (at most 4, zone phrases skipped) and no strong break stand between: "door on the north
              side", "the stairs, blue ones". If that object already has one, it is a second target
              of the same kind ("not the north door, the south one").
  lone        a qualifier no object took is a place only where it ends its phrase: at the end of the
              line, before punctuation or before a lone_follow word. Before a lone_block word or a
              zone phrase ("yellow ping", "main hall") and after a lone_not_after word ("i'm red") it
              is nothing; before any other word it is a target flagged "unsure". Its object is the
              qualifier's "lone" object (blue -> stairs, main -> door); a compass word has none, so
              the target has only a qualifier (a direction).
  zone        a zone belongs to a target only inside its noun phrase: right before it (at most one
              zone_before_fill word) or after it with only zone_after_fill words (at most 3) between.
              Any other zone is a target of its own.
  role        looking back at most 5 tokens from a target (not across punctuation, "you" or another
              target): role_not -> "not", role_from -> "from", role_mine -> "mine", role_them or a
              number followed by a number_next word -> "them"; else, if a status_next word follows the
              target, "status". These are places the bot is NOT sent to.
  primary     the first target without a role; if all have one, the first target.

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
AFTER_MAX = 4
ZONE_AFTER_MAX = 3
MAX_PHRASE_TOKENS = 4
SECTIONS = ("version", "objects", "qualifiers", "named", "zones", "ignore", "words")
WORD_LISTS = ("before_fill", "after_fill", "tail", "zone_before_fill", "zone_after_fill", "lone_follow",
              "lone_block", "lone_not_after", "unknown_modifier", "role_not", "role_from", "role_mine",
              "role_them", "number", "number_next", "status_next", "role_stop", "report_verb", "other",
              "determiner", "neutral_modifier")


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
    toks = tokenize(text)
    words = [t[0] for t in toks]
    n, W = len(toks), vocab["w"]
    mentions, i = [], 0
    while i < n:
        for k in range(min(vocab["max_len"], n - i), 0, -1):
            hit = vocab["phrases"].get(tuple(words[i:i + k]))
            # a phrase does not run across punctuation ("first, floor")
            if hit and not any(toks[j][3] for j in range(i + 1, i + k)):
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

    # 1d. "the spiral staircase", "that broken window", "the left-hand window": one or two words the
    # vocabulary does not know between a determiner and an unqualified object single out one object
    for t in targets:
        if "twin" in t or t["flag"] or t["qualifier"] is not None:
            continue
        f = t["first"]
        for k in (1, 2):
            mid = range(f - k, f)
            if f - k - 1 >= 0 and words[f - k - 1] in W["determiner"] and not any(toks[j][3] for j in range(f - k, f + 1))                     and all(kind_at.get(j) is None and words[j] not in W["neutral_modifier"]
                            and words[j] not in W["determiner"] for j in mid):
                t["flag"] = "unknown_modifier"
                break

    # 2. a free qualifier after an object
    for k, q in enumerate(quals):
        if not free[k]:
            continue
        prev = [o for o in objects if o["last"] < q["first"]]
        if not prev:
            continue
        o = prev[-1]
        t = by_obj[id(o)]
        g = gap(o["last"], q["first"], skip=("zone",))
        if (q["value"] in vocab["allowed"][t["object"]] and len(g) <= AFTER_MAX and set(g) <= W["after_fill"]
                and brk(o["last"], q["first"]) < 2
                and not any(kind_at.get(j) == "qualifier" for j in range(o["last"] + 1, q["first"]))):
            free[k] = False
            nxt = q["last"] + 1
            last = q["last"] + (1 if nxt < n and words[nxt] in W["tail"] and not toks[nxt][3] else 0)
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

    # 3. lone qualifiers: a place only where the word ends its phrase
    for k, q in enumerate(quals):
        if not free[k]:
            continue
        if q["first"] > 0 and not toks[q["first"]][3] and words[q["first"] - 1] in W["lone_not_after"]:
            continue                       # "i'm red"
        nxt = q["last"] + 1
        flag = None
        if nxt < n and not toks[nxt][3] and words[nxt] not in W["lone_follow"]:
            if words[nxt] in W["lone_block"] or kind_at.get(nxt) == "zone":
                continue                   # "yellow ping", "main hall"
            flag = "unsure"                # "hold blue tight", "the white van"
        obj = vocab["lone"][q["value"]]
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
                g = gap(z["last"], t["first"])
                if len(g) <= 1 and set(g) <= W["zone_before_fill"] and brk(z["last"], t["first"]) < 2:
                    best = best or t
            elif z["first"] > t["last"] or (t["obj"] is not None and t["obj"]["last"] < z["first"] <= t["last"]):
                a = t["obj"]["last"] if t["obj"] is not None and z["first"] <= t["last"] else t["last"]
                g = gap(a, z["first"])
                if (len(g) <= ZONE_AFTER_MAX and set(g) <= W["zone_after_fill"] and brk(a, z["first"]) < 2
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
    for t in targets:
        j, steps = t["first"] - 1, 0
        while j >= 0 and steps < ROLE_WINDOW:
            if toks[j + 1][3] or words[j] in W["role_stop"] or j in owned:
                break
            w = words[j]
            if w in W["role_not"]:
                t["role"] = "not"
            elif w in W["role_from"]:
                t["role"] = "from"
            elif w in W["role_mine"]:
                if words[j + 1] in W["report_verb"]:     # "I said the west door": not the player's place
                    break
                t["role"] = "mine"
            elif w in W["role_them"] or (w in W["number"] and words[j + 1] in W["number_next"]):
                t["role"] = "them"
            if t["role"]:
                break
            j -= 1
            steps += 1
        e = t["last"] + 1
        if t["role"] is None and e < n and words[e] in W["status_next"] and not toks[e][3]:
            t["role"] = "status"

    # 5b. a correction reaches back: "smoke blue stairs, no wait, not blue, I meant white"
    for k, t in enumerate(targets):
        if t["role"] == "not" and t["qualifier"] is not None:
            for u in targets[:k]:
                if u["role"] is None and u["qualifier"] == t["qualifier"] and u["object"] in (t["object"], None):
                    u["role"] = "not"
    # 5c. "I've got the north door, you take the other one": only the player's place is named, and the
    # line asks for the other one -> another object of that kind
    if targets and all(t["role"] in ("mine", "status") for t in targets):
        t = targets[-1]
        if t["object"] is not None and any(words[j] in W["other"] for j in range(t["last"] + 1, n)):
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


def run_dev(path=None):
    """The developer's regression lines: {cat, text, accept: [[object, qualifier, zone] | null |
    "FLAG" | "ROLE"]}. Tuning material, never a test set."""
    cases = json.load(io.open(path or os.path.join(HERE, "locations_dev.json"), encoding="utf-8"))["cases"]
    fails = {}
    for c in cases:
        t = find(c["text"])["target"]
        got = None if t is None else [t["object"], t["qualifier"], t["zone"]]
        ok = got in [a for a in c["accept"] if not isinstance(a, str)] or \
            ("FLAG" in c["accept"] and t and t["flag"]) or ("ROLE" in c["accept"] and t and t["role"])
        if not ok:
            fails.setdefault(c["cat"], []).append((c["text"], got, c["accept"]))
    n_fail = sum(map(len, fails.values()))
    print(f"{len(cases)} dev lines, {n_fail} with a primary target the line's author would not accept")
    for cat, rows in fails.items():
        for text, got, want in rows:
            print(f"  [{cat}] {text!r}: got {got}, want {want}")
    return n_fail


if __name__ == "__main__":
    if "--dev" in sys.argv:
        sys.exit(1 if run_dev() else 0)
    for line in sys.argv[1:]:
        print(json.dumps({"text": line, **record(line), "strip": normalized(line, "strip")}))
