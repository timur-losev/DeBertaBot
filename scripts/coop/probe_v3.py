"""
v3, POST-REVIEW probes of the final model: exploratory and NOT blind. They were written during the
review of 2026-10-03/04 (review_v3/README.md), after every v3 blind line and the first results had
been seen, most of them after a first look at what the model answers. The lines are templates, and
the reading of each (this is a callout, that is an order to walk, not to rope) is the developer's
and the reviewers': no author, no annotators. So these are counts of what two bots do on fixed
lines, not accuracy figures, and none of the lines may be used as a test after the model is tuned on
what they show.

Two bots, each loaded on CPU through coop_bot.Bot from a directory given on the command line, each
with its own gate and threshold (bot_config.json): the final v3 model and the shipped v2 model.
Every line goes through Bot.classify and Bot.decide alone (nothing queued from the line before).
Bot.respond is never called, so nothing is appended to coop_bot_log.jsonl. A bot ACTS on a line
when decide() answers anything but "say again" (under the threshold), "ignore" (NONE) or "negated".

(a) smoke-state callouts: "<place> is smoked", "there's smoke on <place>", ... (acting = a second smoke)
(b) clear callouts without a copula ("<place> clear", "clear on <place>", "<place> cleared"), and
    with one ("<place> is clear") as the safe control (acting = the bot pushes in)
(c) orders to go to the roof with no rope word, verb x preposition, and the same wording with
    "top floor" as the control (spec_v3: walking to the roof is MOVE_TO, RAPPEL needs the rope)
(d) "take <colour> stairs" against "take <colour>"
(e) the 233 seed commands of seed_commands_v21.json in ALL CAPS (as written, both bots trained on them)
(f) controls: the plain order "smoke <place>" and the callout "two on <place>"
Place names: the dictionary's own (locations.json: qualifier + object, floors, lone names) and fixed
names outside it. The lists are the reviewers' (their scratch probes), so the counts can be compared
with the review's findings.

    python probe_v3.py ../../models/coop-deberta-v3-ens3-v3 ../../models/coop-deberta-v3-ens3-v2 > probe_v3.log
                       # final v3, shipped v2 (the defaults); jev environment; writes results_v3_probe.json
    python probe_v3.py ../../models/coop-deberta-v3-ens3-v31 ../../models/coop-deberta-v3-ens3-v3 results_v31_probe.json > probe_v31.log
                       # another pair of bots (the first is printed in the "v3" column, the second in "v2"); a
                       # third argument names the results file. Seed set v31 was written against these very
                       # probes, so for a v31 model they show whether the fix took, not how well it generalises
"""
import gc, hashlib, io, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["COOP_TAG"] = "v3"      # coop_v2 as the final model was trained: its families and its training rows
import coop_v2 as V  # noqa: E402
import coop_bot as B  # noqa: E402

MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "models"))
ACT = ("act", "queued", "execute", "go", "wait")      # what decide() does with a line it takes as an order

VOC = json.load(io.open(os.path.join(HERE, "locations.json"), encoding="utf-8"))
NAMED = [f"{q} {o['words'][0]}" for o in VOC["objects"] for q in o["qualifiers"]]     # main door .. brown stairs
FLOORS = [z["words"][0] for z in VOC["zones"] if z["id"] not in ("up", "down")]        # "upstairs" is a direction
COLOURS = [q["words"][0] for q in VOC["qualifiers"] if q["lone"] == "stairs"]
LONE = [q["words"][0] for q in VOC["qualifiers"] if q["lone"]]                         # main + the colours
FURNITURE = ["sofa", "couch", "table", "chairs"]      # the reviewer's four; each is a word of the dictionary
assert all(any(w in o["words"] for o in VOC["objects"] if not o["qualifiers"]) for w in FURNITURE)
# as players call them out, no article: 20 dictionary names + 10 outside
KNOWN = NAMED + FLOORS + [q for q in LONE if q not in COLOURS]
NEW = ["back door", "side door", "garage door", "kitchen window", "green stairs", "black stairs",
       "kitchen", "garage", "attic", "lobby"]
# with the article, as in an order: 23 dictionary names + 24 outside
KNOWN_THE = [n if n.endswith("stairs") else "the " + n for n in NAMED + FURNITURE + FLOORS]
NEW_THE = ["the back door", "the side door", "the garage door", "the kitchen door", "the green door",
           "the back window", "the kitchen window", "the left window", "the top window",
           "green stairs", "black stairs", "orange stairs", "purple stairs", "the back stairs",
           "the desk", "the fridge", "the crates", "the bookshelf", "the bar",
           "the kitchen", "the garage", "the attic", "the lobby", "the server room"]
EIGHT = ["north door", "blue stairs", "basement", "top floor", "roof", "main", "east window", "garage"]
assert set(EIGHT) <= set(KNOWN + NEW)
NEW_COLOURS = ["green", "black", "orange", "purple", "pink", "grey"]

SMOKE_FORMS = ["{} is smoked", "{} is already smoked", "{}'s smoked", "{} smoked", "they smoked {}", "i smoked {}",
               "there's smoke on {}", "{} is smoked off, can't see anything", "i already smoked {}"]
SMOKE_NO_PLACE = ["it's smoked", "already smoked", "that's smoked", "site is smoked", "it's already smoked",
                  "they smoked it", "smoked", "that door is smoked"]
CLEAR_BARE = ["{} clear", "clear on {}", "{} cleared", "{} clear, moving up", "{} all clear"]
CLEAR_COPULA = ["{} is clear", "{}'s clear", "{} looks clear", "{} is clear, nobody there"]
# the 'clear' lines of the reviewer's no-place list (the smoke ones are above); the last three have a copula
CLEAR_NO_PLACE = ["clear", "room clear", "door clear", "stairs clear", "window clear", "all clear",
                  "it's clear", "site is clear", "the door is clear"]
VERBS = ["go", "get", "move", "head", "climb", "run", "come"]
ROOF_FORMS = ["to the roof", "up to the roof", "on the roof", "up on the roof", "onto the roof", "roof"]
# written by a reviewer before any model was run (gap-final-v3-model-behaviour, probes_pre.py)
ROOF_ORDERS = [
    "get up on the roof", "get on the roof", "go roof", "go to the roof", "head up to the roof", "get to the roof",
    "move to the roof", "go up on the roof", "get up to the roof now", "roof, go", "take the roof",
    "i need you on the roof", "get yourself onto the roof", "head for the rooftop", "go to the rooftop",
    "up to the roof, quick", "make your way to the roof", "get on the rooftop", "bot, get on the roof",
    "you go to the roof", "run to the roof", "take the stairs to the roof", "go up the stairs to the roof",
    "get up on that roof and stay there", "i want you up on the roof", "go on up to the roof",
    "move up to the rooftop", "get onto the roof", "go stand on the roof", "walk up to the roof"]


def rows(forms, places, **tags):
    return [dict(tags, form=f, place=p, text=f.format(p)) for f in forms for p in places]


def probes():
    seeds = json.load(io.open(os.path.join(HERE, "seed_commands_v21.json"), encoding="utf-8"))
    seeds = [(k, t) for k, v in seeds.items() if not k.startswith("_") for t in v]
    names = [(p, "dictionary") for p in KNOWN] + [(p, "outside") for p in NEW]
    names_the = [(p, "dictionary") for p in KNOWN_THE] + [(p, "outside") for p in NEW_THE]
    by = lambda form, table: [dict(form=form, place=p, kind=k, text=form.format(p)) for p, k in table]   # noqa: E731
    return {
        "a_smoked_47": by("{} is smoked", names_the),
        "a_smoke_forms": rows(SMOKE_FORMS, EIGHT),
        "a_smoke_no_place": [{"form": t, "text": t} for t in SMOKE_NO_PLACE],
        "b_clear_30": by("{} clear", names),
        "b_clear_47": by("{} clear", names_the),
        "b_clear_forms": rows(CLEAR_BARE, EIGHT, copula=False) + rows(CLEAR_COPULA, EIGHT, copula=True),
        "b_clear_no_place": [{"form": t, "text": t} for t in CLEAR_NO_PLACE],
        "c_roof_grid": [{"form": f, "verb": v, "text": f"{v} {f}"} for f in ROOF_FORMS for v in VERBS],
        "c_top_floor_grid": [{"form": f, "verb": v, "text": f"{v} {f}"}
                             for f in (f.replace("roof", "top floor") for f in ROOF_FORMS) for v in VERBS],
        "c_roof_orders": [{"form": t, "text": t} for t in ROOF_ORDERS],
        "d_take_stairs": [{"form": "take {} stairs", "place": c, "kind": k, "text": f"take {c} stairs"}
                          for c, k in [(c, "dictionary") for c in COLOURS] + [(c, "outside") for c in NEW_COLOURS]],
        "d_take_lone": [{"form": "take {}", "place": c, "kind": k, "text": f"take {c}"}
                        for c, k in [(c, "dictionary") for c in LONE] + [(c, "outside") for c in NEW_COLOURS]],
        "e_seeds_as_written": [{"label": k, "text": t} for k, t in seeds],
        "e_seeds_caps": [{"label": k, "text": t.upper()} for k, t in seeds],
        "f_smoke_order": by("smoke {}", names),
        "f_two_on": by("two on {}", names),
    }


def run(model_dir, texts):
    """What one bot does with each line: the gate's intent and confidence, the pick (NONE under the
    threshold) and decide()'s action."""
    cfg = json.load(io.open(os.path.join(model_dir, "bot_config.json"), encoding="utf-8"))
    bot = B.Bot(model_dir=model_dir)
    out = {}
    for t in texts:
        bot.pending = None        # each line alone: no order left queued by the line before
        bot.classify(t)
        rec = bot.decide(t, bot.last_probs)[1]
        out[t] = {"intent": rec["intent"], "prob": round(rec["prob"], 4), "action": rec["action"],
                  "pick": rec["intent"] if rec["prob"] >= rec["threshold"] else "NONE"}
    info = {"dir": os.path.basename(os.path.normpath(model_dir)), "gate": bot.gate, "threshold": bot.threshold,
            "trained_on": cfg.get("recipe", {}).get("device", "a device bot_config.json does not record")}
    del bot
    gc.collect()
    return out, info


def acts(R, sl):
    return [r for r in sl if R[r["text"]]["action"] in ACT]


def cell(R, sl):
    """'acts on n/N' and with which intents."""
    a = acts(R, sl)
    c = Counter(R[r["text"]]["intent"] for r in a)
    return f"{len(a):>2}/{len(sl)}" + (" " + ", ".join(f"{k} {n}" for k, n in c.most_common()) if a else "")


def conf(R, sl):
    p = sorted(R[r["text"]]["prob"] for r in acts(R, sl))
    return f"confidence {p[0]:.2f}..{p[-1]:.2f}, median {p[len(p) // 2]:.2f}" if p else ""


def one(R, t):
    r = R[t]
    return f"{r['intent']} {r['prob']:.2f} {r['action']}"


def table(OUT, sl, key="form", width=38):
    """One row per form: on how many of its lines each bot acts."""
    for f in dict.fromkeys(r[key] for r in sl):
        sub = [r for r in sl if r[key] == f]
        print(f"    {f:<{width}} " + "   ".join(f"{b} {cell(OUT[b], sub):<26}" for b in OUT).rstrip())
    print(f"    {'all':<{width}} " + "   ".join(f"{b} {cell(OUT[b], sl):<26}" for b in OUT).rstrip())


def split(OUT, sl):
    """acts on n/N for each bot, dictionary names and names outside it apart."""
    for b, R in OUT.items():
        parts = ", ".join(f"{k} {len(acts(R, [r for r in sl if r['kind'] == k]))}/{sum(r['kind'] == k for r in sl)}"
                          for k in dict.fromkeys(r["kind"] for r in sl))
        print(f"    {b}: acts on {cell(R, sl)}   ({parts})   {conf(R, sl)}")


def roof(OUT, sl, train):
    for b, R in OUT.items():
        n = lambda sub, intent: sum(R[r["text"]]["pick"] == intent for r in sub)     # noqa: E731
        under = lambda sub: sum(R[r["text"]]["action"] == "say_again" for r in sub)  # noqa: E731
        print(f"    {b}: RAPPEL {n(sl, 'RAPPEL')}/{len(sl)}, MOVE_TO {n(sl, 'MOVE_TO')}/{len(sl)}, under the threshold "
              f"{under(sl)}/{len(sl)}, other {len(sl) - n(sl, 'RAPPEL') - n(sl, 'MOVE_TO') - under(sl)}")
        if "verb" in sl[0]:
            forms = list(dict.fromkeys(r["form"] for r in sl))
            print("        RAPPEL per form, of 7 verbs: " + "; ".join(
                f"'<verb> {f}' {n([r for r in sl if r['form'] == f], 'RAPPEL')}" for f in forms))
            print(f"        RAPPEL per verb, of {len(forms)} forms: " + "; ".join(
                f"{v} {n([r for r in sl if r['verb'] == v], 'RAPPEL')}" for v in dict.fromkeys(r["verb"] for r in sl)))
            core = [r for r in sl if r["verb"] != "climb" and r["form"] != forms[-1]]      # forms[-1]: the bare noun
            print(f"        without 'climb' and the bare '<verb> {forms[-1]}' rows: RAPPEL {n(core, 'RAPPEL')}/{len(core)}, "
                  f"MOVE_TO {n(core, 'MOVE_TO')}/{len(core)}, under the threshold {under(core)}/{len(core)}")
        fresh = [r for r in sl if r["text"] not in train]
        if len(fresh) < len(sl):
            print(f"        without the training rows of the final v3 model ({len(sl) - len(fresh)}, verbatim): RAPPEL "
                  f"{n(fresh, 'RAPPEL')}/{len(fresh)}, MOVE_TO {n(fresh, 'MOVE_TO')}/{len(fresh)}, under the threshold "
                  f"{under(fresh)}/{len(fresh)}")


def seed_outcomes(R, sl):
    """Per seed command: ok (its label), near (same family), nothing, or a wrong-family pick."""
    out = {"ok": [], "near": [], "nothing": [], "cross": []}
    for r in sl:
        p = R[r["text"]]["pick"]
        out["ok" if p == r["label"] else "nothing" if p == "NONE" else
            "near" if V.FAMILY[p] == V.FAMILY[r["label"]] else "cross"].append(r)
    return out


def main():
    dirs = {"v3": sys.argv[1] if len(sys.argv) > 1 else os.path.join(MODELS, "coop-deberta-v3-ens3-v3"),
            "v2": sys.argv[2] if len(sys.argv) > 2 else os.path.join(MODELS, "coop-deberta-v3-ens3-v2")}
    B.torch.set_num_threads(4)      # about two minutes for both bots; the other cores stay free
    log_before = hashlib.sha256(io.open(B.LOG, "rb").read()).hexdigest() if os.path.exists(B.LOG) else None
    P = probes()
    texts = list(dict.fromkeys(r["text"] for sl in P.values() for r in sl))
    train = {i["text"] for i in V.load_items() + V.seed_items()}
    OUT, info = {}, {}
    for b in ("v2", "v3"):
        OUT[b], info[b] = run(dirs[b], texts)

    print("POST-REVIEW probes (probe_v3.py): exploratory, NOT blind. Written during the review of 2026-10-03/04, after every\n"
          "v3 blind line and the first results were seen. Templated lines; which line is a callout and which an order is the\n"
          "developer's reading, with no annotators. Counts of what the bots do, not accuracy.\n"
          "The families (a)-(e) are the classes of line in which the review found a problem, and most frames were written\n"
          "after a first look at the model's answers. The reviewer's 11 callout / negation frames written before any model\n"
          "was run were clean by the review's count: a wrong action on 0 of 415 lines (v3), on 2 of 415 (v2).")
    for b in ("v2", "v3"):
        i = info[b]
        print(f"  {b} = {i['dir']}: {i['gate']} gate, threshold {i['threshold']:.2f}, trained on {i['trained_on']}")
    print(f"  {len(texts)} distinct lines, each through Bot.classify + Bot.decide on CPU; 'acts' = the line is taken as an order\n"
          "  (not 'say again', not NONE, not stood down by the leading-negation rule)")

    print("\n(a) SMOKE-STATE CALLOUTS (reading: smoke is already there, nothing to do; acting throws another one)")
    print(f"  '<place> is smoked', {len(P['a_smoked_47'])} names with the article ({len(KNOWN_THE)} of the dictionary, {len(NEW_THE)} outside)")
    split(OUT, P["a_smoked_47"])
    print(f"  {len(SMOKE_FORMS)} phrasings x {len(EIGHT)} places ({', '.join(EIGHT)}): acts on n of {len(EIGHT)}")
    table(OUT, P["a_smoke_forms"])
    print("  no place in the line (intent, confidence, action)")
    for r in P["a_smoke_no_place"]:
        print(f"    {r['text']!r:<24} " + "   ".join(f"{b} {one(OUT[b], r['text']):<28}" for b in OUT).rstrip())

    print("\n(b) CLEAR CALLOUTS (reading: the place is empty, nothing to do; acting = ENTRY, the bot pushes in)")
    known = lambda b, key: len(acts(OUT[b], [r for r in P[key] if r["kind"] == "dictionary"]))   # noqa: E731
    bare = {b: len(acts(OUT[b], P["b_clear_no_place"])) for b in OUT}
    print("    the counts on names outside the dictionary depend on the list of names: a verifier of the review, on outside\n"
          "    names of their own, counted v2 10/10 and v3 10/10 without the article, v2 24/24 and v3 21/24 with it. '<name> clear'\n"
          f"    is ENTRY in the shipped v2 bot as well on names outside the dictionary and on lines with no place (of the {len(CLEAR_NO_PLACE)}\n"
          f"    at the end of (b), v2 acts on {bare['v2']} and v3 on {bare['v3']}); the regression of v3 is on dictionary names: "
          f"{known('v2', 'b_clear_30')} -> {known('v3', 'b_clear_30')} of {len(KNOWN)},\n"
          f"    with the article {known('v2', 'b_clear_47')} -> {known('v3', 'b_clear_47')} of {len(KNOWN_THE)}")
    print(f"  '<place> clear', {len(P['b_clear_30'])} names without an article ({len(KNOWN)} of the dictionary, {len(NEW)} outside)")
    split(OUT, P["b_clear_30"])
    print(f"  '<place> clear', the {len(P['b_clear_47'])} names with the article")
    split(OUT, P["b_clear_47"])
    print(f"  phrasings x {len(EIGHT)} places: without a copula")
    table(OUT, [r for r in P["b_clear_forms"] if not r["copula"]])
    print("  with a copula or 'looks' (the safe control: the NONE seeds have '<place> is clear')")
    table(OUT, [r for r in P["b_clear_forms"] if r["copula"]])
    print("  no place in the line (intent, confidence, action); the last three have a copula")
    for r in P["b_clear_no_place"]:
        print(f"    {r['text']!r:<24} " + "   ".join(f"{b} {one(OUT[b], r['text']):<28}" for b in OUT).rstrip())

    print("\n(c) ROOF ORDERS WITHOUT A ROPE WORD (reading, spec_v3: go there on foot = MOVE_TO; RAPPEL is another family)")
    print(f"  grid, {len(VERBS)} verbs ({', '.join(VERBS)}) x {len(ROOF_FORMS)} forms: '<verb> ... roof'")
    print("    'climb' is kept from the reviewer's grid although RAPPEL is a reading one can defend for it: each bot's counts\n"
          "    per verb, and without 'climb' and the bare '<verb> roof' rows, follow its counts per form")
    roof(OUT, P["c_roof_grid"], train)
    print("  control, the same grid with 'top floor' for 'roof'")
    roof(OUT, P["c_top_floor_grid"], train)
    grid = {r["text"] for r in P["c_roof_grid"]}
    print(f"  {len(ROOF_ORDERS)} roof orders a reviewer wrote before running a model "
          f"({sum(r['text'] in grid for r in P['c_roof_orders'])} of them are also lines of the grid)")
    roof(OUT, P["c_roof_orders"], train)
    print("    lines on which v3 answers RAPPEL: " + "; ".join(
        f"{r['text']!r} {OUT['v3'][r['text']]['prob']:.2f}" + (" [training row]" if r["text"] in train else "")
        for r in P["c_roof_orders"] if OUT["v3"][r["text"]]["pick"] == "RAPPEL"))

    take = P["d_take_stairs"] + P["d_take_lone"]
    print("\n(d) 'take <colour> stairs' AGAINST 'take <colour>' (the seed template 'take {}' is MOVE_TO and offers the five lone\n"
          f"    colours, 5 of the {len(P['d_take_lone'])} names of 'take <name>', next to the colour stairs; training rows of v3 among these "
          f"{len(take)} lines:\n"
          f"    {', '.join(repr(r['text']) for r in take if r['text'] in train) or 'none'}. ENTRY for a lone 'take blue' is a reading one\n"
          "    can defend, so this shows a difference, not an error count; the count is for the bare two-word line)")
    for key in ("d_take_stairs", "d_take_lone"):
        sl = P[key]
        print(f"  {sl[0]['form'].format('<name>')!r}, {len(sl)} names: " + "   ".join(f"{b} acts on {cell(OUT[b], sl)}" for b in OUT))
        for r in sl:
            print(f"    {r['text']!r:<22} {r['kind']:<11}" + "   ".join(f"{b} {one(OUT[b], r['text']):<28}" for b in OUT).rstrip())

    print(f"\n(e) THE {len(P['e_seeds_caps'])} SEED COMMANDS OF seed_commands_v21.json (training rows of both bots), as written and in ALL CAPS")
    res_e = {}
    for key, name in (("e_seeds_as_written", "as written"), ("e_seeds_caps", "ALL CAPS")):
        for b, R in OUT.items():
            o = seed_outcomes(R, P[key])
            stood = [r for r in o["cross"] if R[r["text"]]["action"] == "negated"]
            res_e[f"{name}/{b}"] = dict({k: len(v) for k, v in o.items()}, cross_stood_down_by_negation_rule=len(stood))
            print(f"  {name:<10} {b}: the seed's intent {len(o['ok'])}, same family {len(o['near'])}, nothing {len(o['nothing'])}, "
                  f"WRONG FAMILY {len(o['cross'])}" + (f" ({len(stood)} of them stood down by the leading-negation rule)" if stood else ""))
    for b, R in OUT.items():
        print(f"  ALL CAPS, wrong-family picks of {b}: " + "; ".join(
            f"{r['text']!r} ({r['label']}) -> {one(R, r['text'])}" for r in seed_outcomes(R, P["e_seeds_caps"])["cross"]))

    ctrl = P["f_smoke_order"] + P["f_two_on"]
    print("\n(f) CONTROLS on the 30 names of (b)")
    print("    'smoke {}' is a seed template of v3 (make_spec_v3.py), and so are the callouts 'one on {}' and 'two at {}';\n"
          f"    training rows of v3 among these {len(ctrl)} lines, verbatim: {sum(r['text'] in train for r in ctrl)}")
    print("  the plain order 'smoke <place>': " + "   ".join(f"{b} acts on {cell(OUT[b], P['f_smoke_order'])}" for b in OUT))
    print("  the callout 'two on <place>':    " + "   ".join(f"{b} acts on {cell(OUT[b], P['f_two_on'])}" for b in OUT))

    summary = {k: {b: {"acts": len(acts(OUT[b], sl)), "n": len(sl),
                       "intents": dict(Counter(OUT[b][r["text"]]["intent"] for r in acts(OUT[b], sl)).most_common())}
                   for b in OUT} for k, sl in P.items()}
    json.dump({"_note": "POST-REVIEW exploratory probes, NOT blind (probe_v3.py); the readings are the developer's, no annotators. "
                        "Per line and bot: the gate's intent, its confidence, the pick (NONE under the threshold), decide()'s action",
               "bots": info, "summary": summary, "seeds": res_e,
               "probes": {k: [dict(r, **{b: OUT[b][r["text"]] for b in OUT}) for r in sl] for k, sl in P.items()}},
              io.open(os.path.join(HERE, sys.argv[3] if len(sys.argv) > 3 else "results_v3_probe.json"), "w", encoding="utf-8"), indent=1)
    log_after = hashlib.sha256(io.open(B.LOG, "rb").read()).hexdigest() if os.path.exists(B.LOG) else None
    assert log_after == log_before, "coop_bot_log.jsonl changed during the probes"


if __name__ == "__main__":
    main()
