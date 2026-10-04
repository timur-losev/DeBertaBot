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
The authors are the same three personas, so leave-one-author-out holds out an author's v1 and v2
lines together.

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
_I = json.load(io.open(os.path.join(HERE, "intents_v2.json"), encoding="utf-8"))
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
assert set(FAMILY) == set(INTENTS), set(FAMILY) ^ set(INTENTS)
AUTHORS = ["r6", "cs", "stt"]
# which seed set: "v2" (the study) or "v21" (seed_commands_v21.json: + COVER_ME lines with a bare "cover",
# added after the study showed the owner's "cover from behind" going to TAKE_COVER); results files and
# outputs carry the tag, so the v2 study stays as it was
TAG = os.environ.get("COOP_TAG", "v2")
SEED_FILE = {"v2": "seed_commands_v2.json", "v21": "seed_commands_v21.json", "v3": "seed_commands_v3.json"}[TAG]
# "v3": the lines that name map places (blind/v3, annot/v3) join the data, with the seed set that has
# templated location seeds; the v2 / v21 studies load exactly what they loaded before

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
            "target": (t.get("object"), t.get("qualifier"), t.get("zone")), "unknown_modifier": bool(t.get("unknown_modifier"))}


def _target_truth(reads):
    """The place the bot must act on: per field (object, qualifier, zone) the value two of the three
    readers give; "agreed" when two readers give the same whole target."""
    fields = []
    for k in range(3):
        v, n = Counter(r["target"][k] for r in reads).most_common(1)[0]
        fields.append(v if n >= 2 else None)
    whole, n = Counter(r["target"] for r in reads).most_common(1)[0]
    return {"target": tuple(fields), "target_agreed": n >= 2, "target_unanimous": n == 3,
            "unknown_modifier": sum(r["unknown_modifier"] for r in reads) >= 2}


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


def load_items(with_v2=True, with_v3=None):
    """with_v3: the lines that name map places; by default only under COOP_TAG=v3."""
    with_v3 = TAG == "v3" if with_v3 is None else with_v3
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
        for a in auth:
            items.append(_item(a, key, [_read(a)] + [_read(an[a["id"]]) for an in anns], "v3"))
    for it in items:
        for r in it["reads"]:
            assert r["set"] <= set(INTENTS), (it["id"], r)
    return items


def seed_items():
    d = json.load(io.open(os.path.join(HERE, SEED_FILE), encoding="utf-8"))
    out = []
    for intent, lines in d.items():
        if intent.startswith("_"):
            continue
        for n, t in enumerate(lines):
            out.append({"id": f"seed_{intent}_{n}", "text": t, "maj": intent, "accept": {intent},
                        "any": {intent}, "author": "seed", "kind": "seed", "version": "seed"})
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
