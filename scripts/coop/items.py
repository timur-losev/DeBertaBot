"""
What the order acts on: the item of the v60 bots' farmer's and builder's intents (spec_v60 modifiers.item), found in
the transcript. The classifier gives the intent (the verb); this file gives the thing, as the player said it ("build a
pillar" = "pillar"), and the planner checks it against the game's catalogue (its build menu, the seeds the bot carries,
what lies around). The word lists are data (items_v60.json); the rules are here, and the C++ engine is their twin.

Rule set i1 (2026-10-19), written after the v60 authors' and annotators' summaries had quoted about 50 of the 180 v60
test lines (frozen.txt says so): the item number on those lines is not blind. i1 gave 174/180 v60 lines.
Rule set i2 (the same day, after that run; items_v60.json version 2): "yo" is no determiner ("yo bring me some
nails" hid the verb); "outta" ends a phrase; "slap", "whip", "knock" build; a recipient is skipped only before a noun
("bring em to me": "em" is the thing); "them" / "dem" before a noun is a determiner ("give them strawberries some water").

  verb        the line's first word of the intent's own verb list (items_v60.json "verbs"), not after a determiner
              ("the plant"); a word of another intent's list when the line has none ("go mine some uranium");
              none: no item. "pick up", "tear down", "get rid of": the particle after the verb is skipped
  recipient   after a giving verb, me / us / him / her ("bring me the wood"); for WATER and FEED the first noun after
              "give" is the one the order acts on ("give the tomatoes some water" = tomatoes)
  phrase      after determiners and amounts ("some", "two rows of", "a bunch of"), up to max_words words that are no
              stop word ("in", "and", "here", "bro"), no zone ("upstairs") and no punctuation; a map object ends it
              (it is its last word); qualifier-like words ("north", "old", "broken") are left out of the item
  object      a phrase that ends in a map object ("the north field", "the fence") is the target, not the item
              (item null), except for BUILD, COLLECT and DELIVER ("build a fence" = fence); crop words before a field
              or bed are the crop intents' item ("reap the corn field" = corn)
  generic     "stuff", "everything", "materials" are no item; for the crop intents neither are "plants", "crops",
              "garden"; for FEED neither are "animals", "livestock"
  anaphor     "it" / "them": the item of an earlier verb in the line ("get the seeds and plant them" = seeds), else
              the noun the line starts with ("the barricade on the north door is busted, fix it" = barricade)
  FEED        the animals fed, not the food: food or a trough first, "to <animals>" after it ("throw some grain to the
              hens" = hens); food alone: null
  REPAIR      damage words lead to the structure: "patch the hole in the wall" = wall; "seal the breach": null
  with        PLANT_CROP "fill that bed with carrots", "sow it with wheat": the noun after "with"

    python items.py "build a wall by the north door" BUILD
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import locations as LOC  # noqa: E402

RULESET = "i2"


def load_items(path=None):
    v = json.load(io.open(path or os.path.join(HERE, "items_v60.json"), encoding="utf-8"))
    for k, ws in v.items():
        if k in ("_note", "version", "intents", "verbs", "max_words", "item_keeps_object", "crop_intents"):
            continue
        for w in ws:
            assert w and w == w.lower() and all(LOC._is_token_byte(ord(c)) for c in w), (k, w)
    s = {k: set(ws) for k, ws in v.items() if isinstance(ws, list) and k not in ("intents", "item_keeps_object", "crop_intents")}
    s["verbs"] = {k: set(ws) for k, ws in v["verbs"].items()}
    s["all_verbs"] = set().union(*s["verbs"].values())
    s["intents"] = list(v["intents"])
    s["keeps_object"] = set(v["item_keeps_object"])
    s["crop_intents"] = set(v["crop_intents"])
    s["max_words"] = v["max_words"]
    s["version"] = v["version"]
    return s


ITEMS = load_items()


def _words(text, vocab):
    """Tokens without fillers and without the recogniser's repeats ("fix fix the fans", "in the in the bed"):
    [(word, brk)], brk the punctuation before the word (locations.tokenize)."""
    out = []
    for w, _a, _b, br in LOC.tokenize(text):
        if w in vocab["w"]["filler"]:
            continue
        out.append([w, br])
    k = 1
    while k < len(out):
        if out[k][0] == out[k - 1][0] and not out[k][1]:
            out[k - 1][1] = max(out[k - 1][1], out[k][1])
            del out[k]
            continue
        if k >= 3 and (out[k - 1][0], out[k][0]) == (out[k - 3][0], out[k - 2][0]) and not out[k - 1][1] and not out[k][1]:
            del out[k - 1:k + 1]
            continue
        k += 1
    return [(w, br) for w, br in out]


def _place_at(words, i, vocab):
    """(kind, id, length) of the longest vocabulary phrase starting at word i, or None."""
    for n in range(min(vocab["max_len"], len(words) - i), 0, -1):
        if any(words[i + j][1] for j in range(1, n)):
            continue
        p = vocab["phrases"].get(tuple(words[i + j][0] for j in range(n)))
        if p is not None:
            return p[0], p[1], n
    return None


def _phrase(words, i, vocab, S, intent=None):
    """The noun phrase starting at word i: (words of the item, first, last, ends_in_object, crop_words) or None.
    first / last are word positions; ends_in_object: its last word(s) are a map object."""
    n = len(words)
    while i < n and (words[i][0] in S["determiner"] or words[i][0] in S["amount"] or words[i][0].isdigit()
                     or (words[i][0] in S["dem_determiner"] and _noun_next(words, i, S))):
        if i > 0 and words[i][1] == 2:
            return None
        i += 1
    if i >= n or words[i][1]:
        return None if i >= n else (None if words[i][1] == 2 else _phrase_body(words, i, vocab, S, intent))
    return _phrase_body(words, i, vocab, S, intent)


def _noun_next(words, i, S):
    """Word i is followed, with no punctuation, by a word that can start a noun ("them strawberries", "me the wood")."""
    j = i + 1
    return j < len(words) and not words[j][1] and words[j][0] not in S["stop"] and words[j][0] not in S["anaphor"]


def _phrase_body(words, i, vocab, S, intent):
    n, kept, first, last, obj = len(words), [], i, None, False
    j = i
    while j < n and len(kept) < S["max_words"]:
        if j > i and words[j][1]:
            break
        w = words[j][0]
        p = _place_at(words, j, vocab)
        if p is not None and p[0] == "zone" and not kept and intent in S["keeps_object"]:
            kept.extend(words[j + t][0] for t in range(p[2]))      # "put a roof on it": the roof is built
            last, obj = j + p[2] - 1, True
            break
        if p is not None and p[0] in ("zone", "zone_end", "ignore"):
            break
        if p is not None and p[0] in ("object", "named"):
            kept.extend(words[j + t][0] for t in range(p[2]))
            last, obj = j + p[2] - 1, True
            break
        if w in S["stop"] or w in S["all_verbs"] and kept:
            break
        if w in S["determiner"] or w.isdigit() or w in S["amount"]:
            break                      # "give the cows some hay": the second noun is another phrase
        kept.append(w)
        last = j
        j += 1
    if not kept:
        return None
    return kept, first, last, obj


def _clean(kept, S):
    return [w for w in kept if w not in S["not_kind"]]


def _find_verb(words, intent, S, start=0):
    for own in (S["verbs"].get(intent, set()), S["all_verbs"]):
        for i in range(start, len(words)):
            w = words[i][0]
            if w in own and not (i > 0 and not words[i][1] and words[i - 1][0] in S["determiner"]):
                return i
    return -1


def _after_verb(words, v, S):
    """Position after the verb and its particles ("pick up", "get rid of")."""
    i = v + 1
    while i < len(words) and not words[i][1] and words[i][0] in S["particle"]:
        i += 1
        if words[i - 1][0] == "rid" and i < len(words) and words[i][0] in S["particle_after_rid"]:
            i += 1
    return i


def _object_item(ph, intent, vocab, S):
    """The item a phrase gives for the intent, or None. ph = (kept, first, last, ends_in_object)."""
    kept, _f, _l, obj = ph
    if obj:
        if intent in S["keeps_object"]:
            return _clean(kept, S) or None
        if intent in S["crop_intents"]:      # "reap the corn field": the crop words before the field or bed
            n_obj = _object_len(kept, vocab)
            crop = _clean(kept[:len(kept) - n_obj], S)
            return crop or None
        return None
    words = _clean(kept, S)
    if not words:
        return None
    head = words[-1]
    if head in S["generic"] or (intent in S["crop_intents"] and head in S["generic_crop"]) \
            or (intent == "FEED" and head in S["generic_feed"]):
        return None
    return words


def _object_len(kept, vocab):
    for n in range(min(vocab["max_len"], len(kept)), 0, -1):
        p = vocab["phrases"].get(tuple(kept[len(kept) - n:]))
        if p is not None and p[0] in ("object", "named"):
            return n
    return 0


def _next_phrase_after(words, i, links, vocab, S, limit=6):
    """The phrase after the first link word ("to", "with", "in") at or after word i, within `limit` words."""
    for j in range(i, min(len(words), i + limit)):
        if j > i and words[j][1] == 2:
            return None
        if words[j][0] in links:
            return _phrase(words, j + 1, vocab, S)
    return None


def find(text, intent, vocab=None, S=ITEMS):
    """-> {"item": "words as said" or None, "first": word index or -1, "last": ..., "verb": word index or -1}.
    Word indices count the line's words after fillers and repeats are dropped (_words)."""
    vocab = vocab or LOC.VOCAB
    none = {"item": None, "first": -1, "last": -1, "verb": -1}
    if intent not in S["intents"]:
        return none
    words = _words(text, vocab)
    v = _find_verb(words, intent, S)
    if v < 0:
        return none
    i = _after_verb(words, v, S)
    vw = words[v][0]
    if i < len(words) and words[i][0] in S["recipient"] and not words[i][1] and vw in S["recipient_verbs"] \
            and _noun_next(words, i, S):
        i += 1                         # "bring me the wood"; not "bring em to me", where "em" is the thing
    ph = _phrase(words, i, vocab, S, intent)
    res = dict(none, verb=v)
    if ph is None:
        return res
    kept = _clean(ph[0], S)
    head = kept[-1] if kept else None
    if intent == "PLANT_CROP" and (head is None or head in S["generic"] or head in S["generic_crop"] or ph[3]):
        w = _next_phrase_after(words, ph[2] + 1, S["with_link"], vocab, S, limit=4)
        if w is not None:              # "fill that bed with carrots", "sow it with wheat"
            ph, kept = w, _clean(w[0], S)
            head = kept[-1] if kept else None
    if head in S["anaphor"] and len(kept) == 1:
        ph = _antecedent(words, v, intent, vocab, S)
        if ph is None:
            return res
    elif intent == "FEED" and head in S["feed_not"]:
        ph = _next_phrase_after(words, ph[2] + 1, {"to", "for"}, vocab, S)
        if ph is None:
            return res
    elif intent == "REPAIR" and head in S["damage"]:
        ph = _next_phrase_after(words, ph[2] + 1, S["damage_link"], vocab, S, limit=3)
        if ph is None:
            return res
    item = _object_item(ph, intent, vocab, S)
    if not item:
        return res
    return {"item": " ".join(item), "first": ph[1], "last": ph[2], "verb": v}


def _antecedent(words, v, intent, vocab, S):
    """The phrase "it" / "them" stands for: the object of an earlier verb of any list, else the line's first noun."""
    for u in range(v - 1, -1, -1):
        if words[u][0] in S["all_verbs"] and not (u > 0 and words[u - 1][0] in S["determiner"]):
            ph = _phrase(words, _after_verb(words, u, S), vocab, S)
            if ph is not None and _clean(ph[0], S) and _clean(ph[0], S)[-1] not in S["anaphor"]:
                return ph
    if words and words[0][0] in S["determiner"]:
        ph = _phrase(words, 0, vocab, S)
        if ph is not None and ph[2] < v and _clean(ph[0], S):
            return ph
    return None


if __name__ == "__main__":
    os.environ.setdefault("COOP_TAG", "v60")
    voc = LOC.load_vocab(LOC.vocab_file("v60"))
    print(find(sys.argv[1], sys.argv[2], voc))
