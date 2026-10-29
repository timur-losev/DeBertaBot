"""Bot v66 for the Parakeet chain (the v6x line): 71 intents, v64's 69 + GIVE_WAY (step out of the player's way, then keep
following) and WHAT_IS_IT (name the thing the player looks at; family 'see'); the owner's notes of 2026-10-26/27
(make_spec_v66.py; plan: chains2/ml_v66/PLAN_v66.md). build_v65.py's recipe on the v66 data:
  data         v65's lines (none read again: earlier lines with give-way or what-is-it words are pushes and rolls out of the
               way, a vault through glass, "shoot this glass"); seed_commands_v66.json = v65's seeds + 224 (the two intents,
               take it / this / that, throw it, glass is a window, going outside, the boundaries), "let me through" read as
               GIVE_WAY (_relabel_v66)
  owner        owner_lines_v61.json + _v64 + _v65 + owner_lines_v66.json (his English lines of 2026-10-25 22:04 .. 2026-10-27 01:20)
  transcripts  v65's, plus the v66 seeds heard by Parakeet (run_voices_v66.ps1: out_*_v66.json)

    python build_v66.py oof SEED | final SEED | count      (as build_v65.py; all of it in order: run_build_v66.ps1)

build_v65.py's docstring follows.
Bot v65 for the Parakeet chain (the v6x line): no new intent; seeds and owner lines of what the v64 bot got wrong in the
owner's play of 2026-10-25 (make_spec_v65.py; plan: chains2/ml_v65/PLAN_v65.md). build_v64.py's recipe on the v65 data:
  data         v64's (69 intents, v62's and v64's lines); seed_commands_v65.json = v64's seeds + 109 (hide weapon, take = keep,
               put it there, throw it away, getting off a thing and jumping on or over it, don't call me bro), 5 of v64's DELIVER
               seeds read as COLLECT (_relabel_v65)
  owner        the owner's heard lines: owner_lines_v61.json + owner_lines_v64.json (three "take that box" read as COLLECT,
               annot/v65/relabel_v65.json) + owner_lines_v65.json (his English lines of 2026-10-25 17:35..17:43)
  transcripts  v64's, plus the v65 seeds heard by Parakeet (run_voices_v65.ps1: out_*_v65.json)

    python build_v65.py oof SEED | final SEED | count      (as build_v64.py; all of it in order: run_build_v65.ps1)

build_v64.py's docstring follows.
Bot v64 for the Parakeet chain (the v6x line): spec v63's melee and holster and the five of v64 (the report, the body, push,
roll, drop; COLLECT and DELIVER one family), 2026-10-25, make_spec_v64.py. build_v62.py's recipe on the v64 data:

  data         69 intents; v62's lines with three read as the report or the body (annot/v64/relabel_v64.json) + the 180 v64
               lines (all unanimous); seed_commands_v64.json = v62's seeds + spec v63's 126 + 215 (the five, the carry words the
               owner's play missed: lift up, cardboard; bare hands; the boundaries), 11 earlier seeds read as the new intents
  owner        the owner's heard lines (owner_lines_v61.json + owner_lines_v64.json: his English lines of 2026-10-22..25)
  transcripts  v62's, plus the v64 seeds and the v64 lines of r6 and cs heard by Parakeet (run_voices_v64.ps1:
               out_*_v64.json). The accented conditions stay v61's only.

    python build_v64.py oof SEED | final SEED | count      (as build_v62.py; all of it in order: run_build_v64.ps1)

build_v62.py's docstring follows.
Bot v62 for the Parakeet chain (the v6x line): the bot that talks (2026-10-24, make_spec_v62.py). build_v61.py's recipe
(its second build) on the v62 data:

  data         62 intents: v61's 57 + SEE_THING, SEE_ME (one family), SMALL_TALK, PRAISE, KILL_YOURSELF; the teleport is a
               MOVE_TO place (vocabulary v9); v61's lines with three praise lines read as PRAISE (annot/v62/relabel_v62.json)
               + the 120 v62 lines; seed_commands_v62.json = v61's seeds + 331 (the five, the teleport, carrying, the
               boundaries), 15 earlier NONE seeds read as the new intents
  owner        the owner's heard lines (owner_lines_v61.json), three of them read as PRAISE (relabel_v62.json "owner")
  transcripts  v61's, plus the v62 seeds and the v62 lines of r6 and cs heard by Parakeet (run_voices_v62.ps1:
               out_*_v62.json). The accented conditions (ru, de, seedru, seedde) are v61's only: the new seeds and lines
               have none, so they are neither trained on nor tested there.

    python build_v62.py oof SEED | final SEED | count      (as build_v61.py; all of it in order: run_build_v62.ps1)

build_v61.py's docstring follows.

Bot v61 for the Parakeet chain (the v6x line), second build (2026-10-21): build_v60.py's recipe on the v61 data plus what
the speech-to-text makes of a non-native speaker. The owner after playing v61: "постоянно Should получается вместо Shoot.
И улучши распознавание go, вернее нужно обучить на выходах от stt. посмотри логи ещё, найти проблемы, перезатри v61".

  data         v60's 57 intents and lines; seed_commands_v61.json = v60's seeds + what bots v60/v61 did not understand
               in the owner's play (make_spec_v61.py)
  accented     new: every r6/cs line and every seed command read by the Windows voices of other languages (ru: Irina,
               Pavel; de: Hedda, Katja, Stefan; export_accent_v61.py, synth_accent_v61.ps1) and heard by Parakeet:
               conditions ru, de (lines; also tested out of fold) and seedru, seedde. A transcript that keeps less than
               ACCENT_MIN of the line (characters, difflib) or fewer than half its words is left out: "throw the grenade
               there" heard as "So" teaches nothing but a wrong "so". One that loses the line's negation is left out
               too ("don't shoot him" heard as "Then shoot him.")
  owner        new: the owner's own heard lines from the game logs (2026-10-16..21, owner_lines_v61.json: one item per
               line as heard, labelled from the context of the talk), a third group beside lines and seeds: out of fold
               in oof (test id owner|<id>), all of them in the final models

The first build's docstring:
Bot v61 for the Parakeet chain (the v6x line): build_v60.py's recipe on the v61 data -- v60's 57 intents and lines, and
seed_commands_v61.json = v60's seeds + 53 of what bot v60 did not understand in the owner's play (make_spec_v61.py).

The v60 docstring, as it was:
Bot v60 for the Parakeet chain, the farmer and the builder beside the shooter: build_v58.py's recipe on the v60 data
(COOP_TAG=v60: 57 intents, v58's + PLANT_CROP, WATER, HARVEST, TILL, FEED, COLLECT, DELIVER, BUILD, REPAIR, DEMOLISH, each in a
family of its own; v58's lines with their v58 truth (none names farm or build work) + the 180 v60 lines; seed_commands_v60.json =
v58's seeds + 502 of the ten and their boundaries). make_spec_v60.py. The v5x bots go on beside it: the game switches brains.

  lines        all three authors (r6, cs, stt), typed: the 633 older lines, the v5 ... v57 lines and the v60 lines
  seeds        the seed commands of seed_commands_v60.json, typed
  transcripts  what Parakeet TDT 0.6B v2 heard when the r6 and cs lines and the seed commands were read by the
               training voices (Windows, Kokoro English, Kokoro other-language, VCTK pool A): v4's transcripts plus
               the ones of the v5 ... v60 additions (out_*_v5.json ... out_*_v60.json; v58: seeds only); lowercased, final .!?
               stripped, inner punctuation kept; one copy of each (text, label). A transcript carries the label its line has
               under v60.
  epochs       12 (as v4)

    python build_v61.py oof SEED      five folds over lines + seeds; a held-out line is unseen typed and spoken.
                                      A fold that is done is kept in finaloof62_<SEED>.part.json: after a crash the
                                      same command goes on with the next fold
    python build_v61.py final SEED    one model on everything -> models/coop-deberta-v3-ens3-v61/seed<SEED>

VCTK pool B reads test lines only. The device is train_v2.pick_device(): cuda, else mps (Apple silicon), else cpu;
COOP_DEVICE overrides. All of it in order: run_build_v61.ps1.
"""
import difflib, io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v66"
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
import torch
import coop_v2 as V
import train_v2 as T

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = "parakeet-0.6b-v2"
EPOCHS = 12
DEVICE = T.pick_device()
ACCENT = ("ru", "de", "seedru", "seedde")
ACCENT_MIN = 0.4
LINE_TRAIN = ["clean", "kokoro", "kokorox", "vctkA", "ru", "de"]
SEED_TRAIN = ["seedclean", "seedkokoro", "seedkokorox", "seedvctkA", "seedru", "seedde"]
LINE_TEST = ["vctkB", "vctkA", "kokoro", "kokorox", "clean", "ru", "de"]
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v66"))
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()
_heard = {}


def heard(cond):
    """line or seed id -> what Parakeet heard under this condition: v4's audio and the v5 ... v60 additions (v58: seeds only);
    the accented conditions are v61's alone."""
    if cond not in _heard:
        h = {}
        tags = ("_v61",) if cond in ACCENT else \
            ("", "_v5", "_v51", "_v52", "_v53", "_v54", "_v55", "_v56", "_v57") + (("_v58", "_v60", "_v61", "_v62", "_v64", "_v65", "_v66") if cond.startswith("seed") else ("_v60", "_v62", "_v64"))
        for tag in tags:
            d = json.load(io.open(os.path.join(HERE, f"out_{ENGINE}_{cond}{tag}.json"), encoding="utf-8"))
            h.update({r["id"]: norm(r["text"]) for r in d["rows"]})
        _heard[cond] = h
    return _heard[cond]


NEG_SAID = re.compile(r"\b(don'?t|do not|doesn'?t|never|not|no|nobody|nothing|nowhere|stop|cease|quit|without)\b|n't\b")
NEG_HEARD = re.compile(r"(don'?t|do not|doesn'?t|never|\bnot\b|\bno\b|nobody|nothing|nowhere|stop|cease|quit|without|n't\b)")


def kept(said, t):
    """An accented transcript is trained on only if it keeps enough of the line (see the docstring), and keeps its
    negation: the Russian voices' "don't" is often heard as "then" ("don't shoot him" -> "Then shoot him.", labelled
    HOLD_FIRE), which would teach that "then shoot him" stops the shooting (about 200 of the 7474 transcripts)."""
    a, b = words_of(said), words_of(t)
    if NEG_SAID.search(said.lower()) and not NEG_HEARD.search(t.lower()):
        return False
    return bool(b) and difflib.SequenceMatcher(None, a, b).ratio() >= ACCENT_MIN and 2 * len(b.split()) >= len(a.split())


LINES = [i for i in V.load_items() if i["maj"]]
SPOKEN = {i["id"] for i in LINES if i["author"] in ("r6", "cs")}
SEEDS = V.seed_items()
_OWNER_RELABEL = json.load(io.open(os.path.join(HERE, "..", "annot", "v62", "relabel_v62.json"), encoding="utf-8"))["owner"]
_OWNER_RELABEL.update(json.load(io.open(os.path.join(HERE, "..", "annot", "v64", "relabel_v64.json"), encoding="utf-8"))["owner"])
_OWNER_RELABEL.update(json.load(io.open(os.path.join(HERE, "..", "annot", "v65", "relabel_v65.json"), encoding="utf-8"))["owner"])
_OWNER_FILES = ["owner_lines_v61.json", "owner_lines_v64.json", "owner_lines_v65.json", "owner_lines_v66.json"]
OWNER = [{"id": o["id"], "text": o["text"], "maj": _OWNER_RELABEL[o["id"]]["to"] if o["id"] in _OWNER_RELABEL else o["maj"]}
         for f in _OWNER_FILES for o in json.load(io.open(os.path.join(HERE, "..", f), encoding="utf-8"))["items"]]
assert len({o["id"] for o in OWNER}) == len(OWNER), "an owner line id twice"
assert set(V.INTENTS) >= {o["maj"] for o in OWNER}
for _c in LINE_TRAIN + LINE_TEST:   # every voiced line has its transcript; the accented ones only the lines up to v60
    _need = {i for i in SPOKEN if _c not in ACCENT or not i.startswith(("r6v62_", "csv62_", "r6v64_", "csv64_"))}
    assert _need <= set(heard(_c)), (_c, sorted(_need - set(heard(_c)))[:5])
for _c in SEED_TRAIN:
    _need = {s["id"] for s in SEEDS} if _c not in ACCENT else set()
    assert _need <= set(heard(_c)), _c


def words_of(t):
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", t.lower()).split())


def training_set(lines, seeds, owner=()):
    """New in v54: a transcript that is, word for word, a typed line or seed of ANOTHER intent is left out. Parakeet
    heard one command as another one ("now now now" as "no, no, no", "stay" as "okay", "check" as "yeah"), and with
    the answers among the intents such a transcript would teach that "no, no, no" means GO_NOW. 12 of 3080 in the
    full set. The out-of-fold test still gets every transcript as it was heard. v61: the owner's heard lines count as
    typed lines here (they are transcripts already, with the label the talk gives them); an accented transcript must
    also keep enough of its line (kept())."""
    out = [{"id": i["id"], "text": i["text"], "maj": i["maj"]} for i in list(lines) + list(seeds) + list(owner)]
    have = {(i["text"], i["maj"]) for i in out}
    typed = {}
    for i in out:
        typed.setdefault(words_of(i["text"]), set()).add(i["maj"])
    for conds, src in ((LINE_TRAIN, [i for i in lines if i["id"] in SPOKEN]), (SEED_TRAIN, seeds)):
        for cond in conds:
            h = heard(cond)
            for i in src:
                t = h.get(i["id"], "")
                if cond in ACCENT and not kept(i["text"], t):
                    continue
                if t.strip() and (t, i["maj"]) not in have and i["maj"] in typed.get(words_of(t), {i["maj"]}):
                    have.add((t, i["maj"]))
                    out.append({"id": f"{cond}|{i['id']}", "text": t, "maj": i["maj"]})
    return out


def steps(n):
    return (n + T.HP["batch"] - 1) // T.HP["batch"]


if __name__ == "__main__":
    mode, seed = sys.argv[1], int(sys.argv[2])
    t0 = time.time()
    if mode == "oof":
        groups = LINES + SEEDS + OWNER
        random.Random(1000 + seed).shuffle(groups)
        full = EPOCHS * steps(len(training_set(LINES, SEEDS, OWNER)))
        part = os.path.join(HERE, f"finaloof66_{seed}.part.json")      # the folds already done, if this run was cut short
        done = json.load(io.open(part, encoding="utf-8")) if os.path.exists(part) else {"n": len(groups), "folds": [], "probs": {}}
        assert done["n"] == len(groups), f"{part} is from other data: delete it"
        out = done["probs"]
        for f in range(5):
            if f in done["folds"]:
                print(f"oof seed {seed} fold {f}: kept from {os.path.basename(part)}", flush=True)
                continue
            held = {g["id"] for g in groups[f::5]}
            train = training_set([i for i in LINES if i["id"] not in held], [s for s in SEEDS if s["id"] not in held],
                                 [o for o in OWNER if o["id"] not in held])
            test = [{"id": f"owner|{o['id']}", "text": o["text"]} for o in OWNER if o["id"] in held]
            for i in LINES:
                if i["id"] in held:
                    test.append({"id": f"typed|{i['id']}", "text": i["text"]})
                    if i["id"] in SPOKEN:
                        test += [{"id": f"{c}|{i['id']}", "text": heard(c)[i["id"]]} for c in LINE_TEST if i["id"] in heard(c)]
            ep = max(1, round(full / steps(len(train))))
            probs, model, _ = T.train_predict("base", train, test, seed, DEVICE, epochs=ep)
            out.update(probs)
            del model
            T.free_cache(DEVICE)
            done["folds"].append(f)
            json.dump(done, io.open(part, "w", encoding="utf-8"))
            print(f"oof seed {seed} fold {f}: {len(train)} training lines, {ep} epochs, {len(test)} test lines, {DEVICE}, {time.time() - t0:.0f}s", flush=True)
        json.dump({"seed": seed, "epochs": EPOCHS, "device": DEVICE, "probs": out}, io.open(os.path.join(HERE, f"finaloof66_{seed}.json"), "w", encoding="utf-8"))
        os.remove(part)
    elif mode == "count":
        full = training_set(LINES, SEEDS, OWNER)
        by = {}
        for r in full:
            c = r["id"].split("|", 1)[0] if "|" in r["id"] else "typed"
            by[c] = by.get(c, 0) + 1
        print(f"{len(full)} training rows: {len(LINES)} lines, {len(SEEDS)} seeds, {len(OWNER)} owner lines; by source {by}")
        for c in ACCENT:
            src = [i for i in LINES if i["id"] in SPOKEN] if not c.startswith("seed") else SEEDS
            h = heard(c)
            print(f"  {c}: {sum(kept(i['text'], h[i['id']]) for i in src if i['id'] in h)}/{len(src)} transcripts keep enough of their line")
    else:
        train = training_set(LINES, SEEDS, OWNER)
        _, model, tok = T.train_predict("base", train, [{"id": "x", "text": "go"}], seed, DEVICE, epochs=EPOCHS)
        d = os.path.join(OUT_DIR, f"seed{seed}")
        os.makedirs(d, exist_ok=True)
        model.to("cpu").save_pretrained(d, safe_serialization=True)
        tok.save_pretrained(d)
        json.dump({"training_lines": len(train), "typed_lines": len(LINES), "seeds": len(SEEDS), "owner_lines": len(OWNER),
                   "epochs": EPOCHS, "device": DEVICE}, io.open(os.path.join(d, "trained_on.json"), "w"))
        print(f"final seed {seed}: {len(train)} training lines ({len(LINES)} lines + {len(SEEDS)} seeds + {len(OWNER)} owner lines "
              f"typed, {len(train) - len(LINES) - len(SEEDS) - len(OWNER)} heard by Parakeet), {EPOCHS} epochs, {DEVICE}, saved, "
              f"{time.time() - t0:.0f}s", flush=True)
