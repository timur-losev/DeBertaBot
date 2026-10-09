"""
The v2 label set (make_spec_v2.py) as data: 24 intents, their families, the test lines, the seeds,
and the strict scoring. Stdlib only, so both environments can import it.

Test lines ("items")
  v1   the 363 lines of blind/author_*.json; truth = majority of the author and two annotators
       (run_coop.load_test). They were written and read under the 22-intent spec, so each was read
       again under spec_v2.json by one fresh annotator (annot/v2/old_*_v2ann.json). Rule: a v1 line
       whose re-reading picks TAKE_COVER or OPEN as its intent is "flagged"; its v1 reads cannot
       express the new intents, so its truth becomes the majority of three v2 readings (the
       re-reader + two adjudicators in annot/v2/old_adjudicated.json). Every other v1 line keeps its
       v1 truth. (This file was first hashed after the re-reading files existed, so the log cannot
       show the rule came first; no line was flagged, so the rule never applied.)
  v2   blind/v2/author_*.json, 40 lines per author written under spec_v2.json (TAKE_COVER, OPEN and
       the orders they can be confused with); truth = majority of author + two annotators.
  v5   COOP_TAG=v5 (make_spec_v5.py): 27 intents -- ATTACK, OPEN_FIRE and HOLD_FIRE are new -- and
       directions. Every older line (v1, v2, v3) was read again under spec_v5.json by one fresh
       annotator (annot/v5/old_*_v5ann.json). Rule, fixed before the re-reading: an older line whose
       re-reading picks ATTACK, OPEN_FIRE or HOLD_FIRE is "flagged"; its old reads cannot express the
       new intents, so its truth becomes the majority of three v5 readings (the re-reader + two
       adjudicators in annot/v5/old_adjudicated.json). Every other older line keeps its truth. Then
       blind/v5/author_*.json, the lines written under spec_v5.json; truth = majority of author + two
       annotators, and their targets carry a direction.
  v51  COOP_TAG=v51 (make_spec_v51.py): 29 intents -- LOOK_AT and LOOK_AT_ME are new. The same rule one step
       on: every line the v5 tag loads (the older lines and the v5 lines) was read again under spec_v51.json
       (annot/v51/old_*_v51ann.json); a line whose re-reading picks LOOK_AT or LOOK_AT_ME takes the majority
       of three v51 readings (annot/v51/old_adjudicated.json), every other line keeps its truth. Then
       blind/v51/author_*.json, the lines written under spec_v51.json.
  v52  COOP_TAG=v52 (make_spec_v52.py): 32 intents -- HELP, CHECK and SUPPRESS are new, after the owner's
       first test with a real voice. The same rule again: every line the v51 tag loads was read under
       spec_v52.json (annot/v52/old_*_v52ann.json); a line whose re-reading picks one of the three takes the
       majority of three v52 readings. Then blind/v52/author_*.json. One seed carries another label under
       this tag and keeps its id ("help me": REVIVE_ME -> HELP; seed_commands_v52.json "_relabel_v52").
  v53  COOP_TAG=v53 (make_spec_v53.py): 33 intents -- JUMP is new, after the owner's test of bot v52. The same
       rule: every line the v52 tag loads was read under spec_v53.json (annot/v53/old_*_v53ann.json); a line
       whose re-reading picks JUMP takes the majority of three v53 readings. Then blind/v53/author_*.json.
       "_relabel_v53" lists every seed with another label under this tag (v52's and "drop down from the roof").
The authors are the same three personas, so leave-one-author-out holds out all of an author's lines
together.

Scoring (strict: only NONE is doing nothing)
  near        the pick is accepted by two of three readers, or is in the family of their majority
  cross       wrong family: the bot acted and the pick is neither accepted nor in the family
  fired       of the NONE-majority lines, the share where the bot acted
Two gates turn probabilities into a pick:
  top         the top intent, if its probability reaches the threshold
  family      the family with the most probability mass; its top intent, if the family's mass reaches
              the threshold ("break in": BREACH 0.51 + ENTRY 0.47 = 0.98 acts, where top says again)
"""
import glob, io, json, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
# which seed set: "v2" (the study) or "v21" (seed_commands_v21.json: + COVER_ME lines with a bare "cover",
# added after the study showed the owner's "cover from behind" going to TAKE_COVER); results files and
# outputs carry the tag, so the v2 study stays as it was
TAG = os.environ.get("COOP_TAG", "v2")
V5 = TAG in ("v5", "v51", "v52", "v53")    # 27 intents (intents_v5.json); every older tag keeps the 24 of intents_v2.json
V51 = TAG in ("v51", "v52", "v53")         # 29 intents (intents_v51.json): v5 + LOOK_AT, LOOK_AT_ME
V52 = TAG in ("v52", "v53")                # 32 intents (intents_v52.json): v51 + HELP, CHECK, SUPPRESS
V53 = TAG == "v53"                         # 33 intents (intents_v53.json): v52 + JUMP
_I = json.load(io.open(os.path.join(HERE, "intents_v53.json" if V53 else "intents_v52.json" if V52 else "intents_v51.json" if V51 else
                                    "intents_v5.json" if V5 else "intents_v2.json"), encoding="utf-8"))
I = {k: v for k, v in _I.items() if not k.startswith("_")}
INTENTS = list(I)
NEW = {"TAKE_COVER", "OPEN"}
FAMILY = {"BREACH": "assault", "ENTRY": "assault", "VAULT_WINDOW": "assault", "RAPPEL": "assault",
          "FLASH": "utility", "SMOKE": "utility", "FRAG": "utility",
          "HOLD_POSITION": "hold", "HOLD_ANGLE": "hold", "HOLD_OTHER_ANGLE": "hold", "COVER_ME": "hold",
          "FOLLOW_ME": "move", "MOVE_TO": "move", "FLANK": "move",
          "PLANT": "objective", "DEFUSE": "objective", "DRONE": "scout", "REVIVE_ME": "revive",
          "FALL_BACK": "retreat", "WAIT": "stop", "GO_NOW": "go", "NONE": "none",
          "TAKE_COVER": "cover", "OPEN": "open"}
NEW5 = {"ATTACK", "OPEN_FIRE", "HOLD_FIRE"}
if V5:      # each in a family of its own: a plain "attack" is not a breach, and firing is not ceasing fire
    FAMILY.update({"ATTACK": "attack", "OPEN_FIRE": "fire", "HOLD_FIRE": "ceasefire"})
NEW51 = {"LOOK_AT", "LOOK_AT_ME"}
if V51:     # one family: the planner's one command "look"; the top intent says whether it is the player
    FAMILY.update({"LOOK_AT": "look", "LOOK_AT_ME": "look"})
NEW52 = {"HELP", "CHECK", "SUPPRESS"}
if V52:     # HELP is not a revive and CHECK is not a drone: their own families; SUPPRESS is firing, like OPEN_FIRE
    FAMILY.update({"HELP": "help", "CHECK": "check", "SUPPRESS": "fire"})
NEW53 = {"JUMP"}
if V53:     # a jump is a move: a planner that does not know it gets a move with a direction
    FAMILY.update({"JUMP": "move"})
assert set(FAMILY) == set(INTENTS), set(FAMILY) ^ set(INTENTS)
AUTHORS = ["r6", "cs", "stt"]
SEED_FILE = {"v2": "seed_commands_v2.json", "v21": "seed_commands_v21.json", "v3": "seed_commands_v3.json",
             "v31": "seed_commands_v31.json", "v5": "seed_commands_v5.json", "v51": "seed_commands_v51.json", "v52": "seed_commands_v52.json",
             "v53": "seed_commands_v53.json"}[TAG]
# "v3": the lines that name map places (blind/v3, annot/v3) join the data, with the seed set that has
# templated location seeds; the v2 / v21 studies load exactly what they loaded before.
# "v31": the v3 data with the seed set corrected after the v3 review (make_seeds_v31.py), and with the
# independent re-reading of the r6 author's lines (annot/v3/reann_r6.json) in place of the second r6
# annotation, which is byte-identical to the first; the v3 study stays as it was
# "v5": the v31 data read under the 27-intent spec (see the module docstring), the v5 lines and seeds
# "v51": the v5 data read under the 29-intent spec, the v51 lines and seeds
# "v52": the v51 data read under the 32-intent spec, the v52 lines and seeds
# "v53": the v52 data read under the 33-intent spec, the v53 lines and seeds
PLACES = TAG in ("v3", "v31", "v5", "v51", "v52", "v53")

# the owner's own live-test lines with the reading they asked for, and the canonical probes the v1
# live test failed on. Not a blind check: none is a training line verbatim, but most are near copies
# of seed commands (char-n-gram cosine 0.78-0.96; only "break in" is below 0.5), the owner's logged
# "find cover" and "open the door" are v2 seeds, "come here" / "go there" / "breach" / "dont breach"
# are v1 seeds, and the v21 seeds were written because of the two "cover" lines
PROBES = [
    ("go find cover", {"TAKE_COVER"}), ("hide out", {"TAKE_COVER"}), ("hide there", {"TAKE_COVER"}),
    ("cover from behid", {"COVER_ME"}), ("follow me and cover my back", {"COVER_ME", "FOLLOW_ME"}),
    ("cover while moving", {"COVER_ME"}), ("break in", {"BREACH", "ENTRY"}), ("open window", {"OPEN"}),
    ("breach window", {"BREACH", "VAULT_WINDOW"}),
    ("come here", {"FOLLOW_ME"}), ("go there", {"MOVE_TO"}), ("breach", {"BREACH"}),
    ("do not come to me", {"NONE"}), ("don't blow that wall", {"NONE", "WAIT"}),
    ("dont breach", {"NONE", "WAIT"}), ("never flank", {"NONE", "WAIT"}),
]


def _read(a):
    t = a.get("target") or {}
    return {"intent": a["intent"], "set": {a["intent"]} | set(a.get("ok", [])),
            "timing": a.get("timing", "now"), "reference": a.get("reference", "none"),
            "target": (t.get("object"), t.get("qualifier"), t.get("zone")), "unknown_modifier": bool(t.get("unknown_modifier")),
            "direction": t.get("direction")}


def _target_truth(reads):
    """The place the bot must act on: per field (object, qualifier, zone) the value two of the three
    readers give; "agreed" when two readers give the same whole target."""
    fields = []
    for k in range(3):
        v, n = Counter(r["target"][k] for r in reads).most_common(1)[0]
        fields.append(v if n >= 2 else None)
    whole, n = Counter(r["target"] for r in reads).most_common(1)[0]
    d, dn = Counter(r["direction"] for r in reads).most_common(1)[0]
    return {"target": tuple(fields), "target_agreed": n >= 2, "target_unanimous": n == 3,
            "unknown_modifier": sum(r["unknown_modifier"] for r in reads) >= 2,
            "direction": d if dn >= 2 else None, "direction_agreed": dn >= 2}


def _item(a, key, reads, version):
    votes = Counter(r["intent"] for r in reads)
    top, n = votes.most_common(1)[0]
    acc = Counter(i for r in reads for i in r["set"])
    tv = Counter(r["timing"] for r in reads).most_common(1)[0]
    rv = Counter(r["reference"] for r in reads).most_common(1)[0]
    return {"id": a["id"], "author": key, "text": a["text"], "kind": a.get("kind", "plain"),
            "version": version, "maj": top if n >= 2 else None, "unanimous": n == 3,
            "accept": {i for i, c in acc.items() if c >= 2}, "any": set(acc),
            "timing": tv[0] if tv[1] >= 2 else None, "reference": rv[0] if rv[1] >= 2 else None,
            "reads": reads, **_target_truth(reads)}


def reread_flags():
    """v1 line id -> its v2 re-reading, for the lines whose re-reading picks a new intent."""
    out = {}
    for key in AUTHORS:
        p = os.path.join(HERE, "annot", "v2", f"old_{key}_v2ann.json")
        if os.path.exists(p):
            out.update({k: v for k, v in json.load(io.open(p, encoding="utf-8")).items() if v["intent"] in NEW})
    return out


def reread_flags_of(ver, new):
    """line id -> its re-reading under spec <ver>, for the lines whose re-reading picks one of the `new` intents."""
    out = {}
    for key in AUTHORS:
        p = os.path.join(HERE, "annot", ver, f"old_{key}_{ver}ann.json")
        if os.path.exists(p):
            out.update({k: v for k, v in json.load(io.open(p, encoding="utf-8")).items() if v["intent"] in new})
    return out


def reread_flags_v5():
    return reread_flags_of("v5", NEW5)


def _apply(items, ver, new):
    """COOP_TAG=v5 / v51: the flagged lines get their three readings under spec <ver>; then the <ver> lines join."""
    flags = reread_flags_of(ver, new)
    adj_path = os.path.join(HERE, "annot", ver, "old_adjudicated.json")
    adj = json.load(io.open(adj_path, encoding="utf-8")) if os.path.exists(adj_path) else {}
    missing = sorted(set(flags) - set(adj))
    assert not missing, f"flagged lines without {ver} adjudication: {missing}"
    assert set(flags) <= {it["id"] for it in items}, sorted(set(flags) - {it["id"] for it in items})
    out = []
    for it in items:
        if it["id"] in flags:
            a = {"id": it["id"], "text": it["text"], "kind": it["kind"]}
            reads = [_read(flags[it["id"]])] + [_read(x) for x in adj[it["id"]]]
            new_it = _item(a, it["author"], reads, it["version"] + "-reread" + ver[1:])
            # a re-reading gives the intent only: the place stays what the line's own readers said
            for k in ("target", "target_agreed", "target_unanimous", "unknown_modifier", "direction", "direction_agreed"):
                new_it[k] = it[k]
            out.append(new_it)
        else:
            out.append(it)
    for key in AUTHORS:
        auth = json.load(io.open(os.path.join(HERE, "blind", ver, f"author_{key}.json"), encoding="utf-8"))
        anns = [json.load(io.open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(HERE, "annot", ver, f"author_{key}_ann*.json")))]
        assert len(anns) == 2, (key, len(anns))
        for a in auth:
            out.append(_item(a, key, [_read(a)] + [_read(an[a["id"]]) for an in anns], ver))
    return out


def load_items(with_v2=True, with_v3=None):
    """with_v3: the lines that name map places; by default only under COOP_TAG=v3 / v31 / v5."""
    with_v3 = PLACES if with_v3 is None else with_v3
    items = []
    flags = reread_flags()
    adj_path = os.path.join(HERE, "annot", "v2", "old_adjudicated.json")
    adj = json.load(io.open(adj_path, encoding="utf-8")) if os.path.exists(adj_path) else {}
    missing = sorted(set(flags) - set(adj))
    assert not missing, f"flagged v1 lines without adjudication: {missing}"
    for key in AUTHORS:
        auth = json.load(io.open(os.path.join(HERE, "blind", f"author_{key}.json"), encoding="utf-8"))
        anns = [json.load(io.open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(HERE, "annot", f"author_{key}_ann*.json")))]
        assert len(anns) == 2
        for a in auth:
            if a["id"] in flags:
                reads = [_read(flags[a["id"]])] + [_read(x) for x in adj[a["id"]]]
                items.append(_item(a, key, reads, "v1-reread"))
            else:
                reads = [_read(a)] + [_read(an[a["id"]]) for an in anns]
                items.append(_item(a, key, reads, "v1"))
        if not with_v2:
            continue
        auth = json.load(io.open(os.path.join(HERE, "blind", "v2", f"author_{key}.json"), encoding="utf-8"))
        anns = [json.load(io.open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(HERE, "annot", "v2", f"author_{key}_ann*.json")))]
        assert len(anns) == 2, (key, len(anns))
        for a in auth:
            items.append(_item(a, key, [_read(a)] + [_read(an[a["id"]]) for an in anns], "v2"))
        if not with_v3:
            continue
        auth = json.load(io.open(os.path.join(HERE, "blind", "v3", f"author_{key}.json"), encoding="utf-8"))
        anns = [json.load(io.open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(HERE, "annot", "v3", f"author_{key}_ann*.json")))]
        assert len(anns) == 2, (key, len(anns))
        if TAG in ("v31", "v5", "v51", "v52", "v53") and key == "r6":
            anns[1] = json.load(io.open(os.path.join(HERE, "annot", "v3", "reann_r6.json"), encoding="utf-8"))
        for a in auth:
            items.append(_item(a, key, [_read(a)] + [_read(an[a["id"]]) for an in anns], "v3"))
    if V5 and with_v2 and with_v3:
        items = _apply(items, "v5", NEW5)
    if V51 and with_v2 and with_v3:
        items = _apply(items, "v51", NEW51)
    if V52 and with_v2 and with_v3:
        items = _apply(items, "v52", NEW52)
    if V53 and with_v2 and with_v3:
        items = _apply(items, "v53", NEW53)
    for it in items:
        for r in it["reads"]:
            assert r["set"] <= set(INTENTS), (it["id"], r)
    return items


def load_v3b():
    """The second batch of lines that name map places (blind/v3b, annot/v3b): written after rule set v3
    and seed set v31 were fixed. A test set only; no model is trained on it."""
    items = []
    for key in AUTHORS:
        p = os.path.join(HERE, "blind", "v3b", f"author_{key}.json")
        if not os.path.exists(p):
            continue
        auth = json.load(io.open(p, encoding="utf-8"))
        anns = [json.load(io.open(q, encoding="utf-8"))
                for q in sorted(glob.glob(os.path.join(HERE, "annot", "v3b", f"author_{key}_ann*.json")))]
        assert len(anns) == 2, (key, len(anns))
        for a in auth:
            items.append(_item(a, key, [_read(a)] + [_read(an[a["id"]]) for an in anns], "v3b"))
    for it in items:
        for r in it["reads"]:
            assert r["set"] <= set(INTENTS), (it["id"], r)
    return items


def seed_items():
    d = json.load(io.open(os.path.join(HERE, SEED_FILE), encoding="utf-8"))
    relabel = d.get(f"_relabel_{TAG}", {})      # a seed that keeps its id (and its audio) under another label
    out = []
    for intent, lines in d.items():
        if intent.startswith("_"):
            continue
        for n, t in enumerate(lines):
            label = relabel.get(f"seed_{intent}_{n}", intent)
            out.append({"id": f"seed_{intent}_{n}", "text": t, "maj": label, "accept": {label},
                        "any": {label}, "author": "seed", "kind": "seed", "version": "seed"})
    assert set(relabel) <= {s["id"] for s in out}, sorted(set(relabel) - {s["id"] for s in out})
    return out


def probe_items():
    return [{"id": f"probe_{n}", "text": t, "maj": sorted(w)[0], "accept": set(w), "any": set(w),
             "author": "probe", "kind": "probe", "version": "probe"} for n, (t, w) in enumerate(PROBES)]


# ---------------------------------------------------------------- picks and scores

def pick(row, gate, thr):
    """(intent, confidence) -> the bot's pick; below the threshold the bot does nothing (NONE)."""
    if gate == "top":
        j = max(range(len(row)), key=row.__getitem__)
        return (INTENTS[j] if row[j] >= thr else "NONE"), row[j]
    mass = {}
    for j, p in enumerate(row):
        mass[FAMILY[INTENTS[j]]] = mass.get(FAMILY[INTENTS[j]], 0.0) + p
    fam = max(mass, key=mass.get)
    j = max((j for j in range(len(row)) if FAMILY[INTENTS[j]] == fam), key=row.__getitem__)
    return (INTENTS[j] if mass[fam] >= thr else "NONE"), mass[fam]


def confidence(row, gate):
    return pick(row, gate, 0.0)


def picks(probs, gate, thr):
    return {k: pick(row, gate, thr)[0] for k, row in probs.items()}


def score(preds, items):
    """Strict counts, as fractions of the items; only NONE is doing nothing."""
    n = len(items)
    near = cross = fired = n_none = ok = 0
    for it in items:
        p = preds[it["id"]]
        good = p in it["accept"] or bool(it["maj"] and FAMILY[p] == FAMILY[it["maj"]])
        near += good
        ok += p in it["accept"]
        if not good and p != "NONE":
            cross += 1
        if it["maj"] == "NONE":
            n_none += 1
            fired += p != "NONE"
    return {"n": n, "near": near / n, "ok": ok / n, "cross": cross / n,
            "fired_on_nonorder": fired / max(n_none, 1), "near_count": near, "cross_count": cross}


def fit_threshold(probs, items, gate):
    """Threshold maximising near_count - 2 * cross_count (integer counts; ties -> lowest threshold),
    on a 0.00..0.98 grid, like select_bert.criterion."""
    sub = [i for i in items if i["id"] in probs]
    best = None
    for t in range(0, 100, 2):
        s = score(picks(probs, gate, t / 100), sub)
        v = s["near_count"] - 2 * s["cross_count"]
        if best is None or v > best[0]:
            best = (v, t / 100)
    return best[1], best[0]
