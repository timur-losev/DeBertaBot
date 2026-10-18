"""Round five of the chains study (chain v58 over bot v57, 2026-10-18): the game's rewriter trained again after the owner's play.
Why: of the owner's 689 spoken lines of 2026-10-16..18 (the context audit), about fifteen orders that lean on the order before
them went wrong, and on about ten of them the decoder was asked and wrote the line back as it was: a pronoun for the thing the
last order named ("Get inside of it." after "Get to the car." sent the bot indoors), getting out of the car the bot sits in
("Move out."), going on with a movement ("Keep moving.", "Further up.", "More up."), "another" after an order on a thing.
What changes against round four's pieces4d_final (chains3_v55.py):
  - the labels are v57's (47 intents) and the calculator is the v57 ensemble: a piece is kept when it reads as labelled;
  - spec_context_v58.json: rules 5b (a pronoun for the last order's thing makes the line incomplete), 5c (getting in and out of
    the vehicle the talk is about), 12 (going on with a movement), 13 (a repeat with a place is written back as it is), 6c (a
    "no" and an order of its own is that order), 4c ("another" after an order on a thing). New items: chains2/ctx_teacher_v58_*.json
    (three AI authors, 60 each, blind to the owner's lines), in V58_COPIES copies with older lines in front, and the r6 and cs
    ones also as heard from four voices (chains2/ctx_teacher_v58_heard.json, voice_chains.py train + train2);
  - the owner's own lines are a test set only (chains2/owner_ctx_v58.json, owner_ctx_score.py), never trained on.
Everything else is round four's recipe (Qwen3-1.7B, QLoRA r16, three epochs, the rows of pieces4d_final).

    python chains4_v58.py check     every context item (round four's kept ones, the v58 ones) read by the v57 ensemble -> chains2/ctx_checked_v58.json
    python chains4_v58.py train     pieces5_final seed 0 -> models/coop-qwen3-qlora-chains4-v58/pieces5_final_seed0, and its answers
                                    on round three's test sets -> chains4_58_pieces5_final_s0.json
    python chains4_v58.py gguf      the adapter merged, as GGUF in 4 bits (gguf_v54.py make)
    python chains4_v58.py export    models/coop-chain-v58/cpp for the engine (export_chain_cpp.py; router_v58.py first)
    python chains4_v58.py score     round three's blind sets: round four's game decoder against this round's -> chains4_58_score.log
The owner's set: python owner_ctx_score.py <coop_cli.exe> <bot cpp> models/coop-chain-v58/cpp (and the same with coop-chain-v55).
"""
import io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v57"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, COOP)
import coop_v2 as V                    # the v57 vocabulary, imported first: the scripts below set COOP_TAG=v54 when they load
import build_v57
sys.modules["build_v54"] = build_v57   # they import build_v54 by name; they get the v57 lines and seeds
import torch
import qlora_v54 as Q
import chains_v54 as C
import chains2_v54 as C2
import coop_bot
assert V.TAG == "v57" and len(V.INTENTS) == 47, (V.TAG, len(V.INTENTS))

C.BOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v57"))   # the calculator
VARIANT, ROWS_OF = os.environ.get("CHAINS4_VARIANT", "pieces5_final"), "pieces3"
V55_COPIES = V58_COPIES = 6             # as pieces4d_final's v55 items
CTX_EXTRA = ((0, 0.4), (1, 0.25), (2, 0.2), (3, 0.15))     # per copy of a context item, at most five earlier lines in all
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = ROWS_OF
ADAPTER = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-qwen3-qlora-chains4-v58"))
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}")
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains4_58_{variant}_s{seed}.json")
CHECKED_V55 = os.path.join(C2.CH2, "ctx_checked_v55.json")
CHECKED = os.path.join(C2.CH2, "ctx_checked_v58.json")
HEARD_V58 = os.path.join(C2.CH2, "ctx_teacher_v58_heard.json")
AUTHORS = ("r6", "cs", "stt")
# fixed before training, as round four: how many unrelated earlier lines go in front of a row that has none of its own
P_CONTEXT, N_BEFORE = 0.5, ((1, 0.35), (2, 0.25), (3, 0.15), (4, 0.12), (5, 0.13))


RELABEL_V56 = {"REVIVE_ME": "HELP_INTERACTION"}   # bot v56: "revive me", "let me out" walk to the speaker (the owner's choice)


# The authors' files stay as they wrote them; what the first check (2026-10-18) showed is mended here. The v57 ensemble reads
# "keep moving forward", "keep going left", "keep coming back" as no order and "move further forward", "move further left",
# "come back to me" as the orders (probe_v57.py), so rule 12 now rewrites with "further" / "more" (spec_context_v58.json) and
# the items that wrote "keep"/"continue" get those words. A line kept as it is that the bot cannot act on reads NONE. Items
# whose label is in dispute between two readings ("push" as ENTRY or a move, a repeat with a side read as a callout, the
# other stairs as HOLD_OTHER_ANGLE, climbing on a car as getting in) are left out: None.
CURATE = {
    "x58_r6_008": (["Come back to me."], ["COME_BACK"]),
    "x58_r6_010": (["Move up to the west window."], ["MOVE_TO"]),
    "x58_r6_017": (["Keep moving."], ["NONE"]),
    "x58_r6_033": (["Go further up the hallway."], ["MOVE_TO"]),
    "x58_r6_039": None,
    "x58_r6_046": None,
    "x58_cs_023": (["go further forward"], ["MOVE_TO"]),
    "x58_cs_030": None,
    "x58_cs_037": None,
    "x58_cs_039": None,
    "x58_cs_053": (["ok keep moving"], ["NONE"]),
    "x58_stt_013": None,
    "x58_stt_024": (["move further forward"], ["MOVE_TO"]),
    "x58_stt_027": (["move further left"], ["MOVE_TO"]),
    "x58_stt_031": (["move further right"], ["MOVE_TO"]),
    "x58_stt_037": None,
    "x58_stt_045": (["throw a frag over there"], ["FRAG"]),
    "x58_stt_051": None,
    "x58_stt_053": (["okay keep moving"], ["NONE"]),
}


def v58_context():
    """Round four's kept context items (spec_context_v55 applied, v56's renamed intent), then the v58 authors' items as CURATE
    mends them."""
    old = [dict(x) for x in C2.jload(CHECKED_V55) if x["kept"]]
    for x in old:
        x["orders"] = [RELABEL_V56.get(o, o) for o in x["orders"]]
    new = []
    for v in AUTHORS:
        for x in C2.jload(C2.CH2, f"ctx_teacher_v58_{v}.json"):
            if x["id"] in CURATE:
                if CURATE[x["id"]] is None:
                    continue
                x = dict(x, pieces=CURATE[x["id"]][0], orders=CURATE[x["id"]][1], curated=True)
            new.append(x)
    return old, new


def context_kept():
    """The context items of round five that the calculator kept (chains2/ctx_checked_v58.json)."""
    return [x for x in C2.jload(CHECKED) if x["kept"]]


def check():
    old, new = v58_context()
    picks, cfg = C.bot_picks([{"id": f"{t['id']}#{k}", "text": p} for t in old + new for k, p in enumerate(t["pieces"])])
    print(f"calculator: {C.BOT} (gate {cfg['gate']}, threshold {cfg['threshold']})")
    for label, items in (("round four's items", old), ("v58 items", new)):
        n = agree = 0
        for t in items:
            assert len(t["orders"]) == len(t["pieces"]) and set(t["orders"]) <= set(V.INTENTS), t["id"]
            got = [picks[f"{t['id']}#{k}"][0] for k in range(len(t["pieces"]))]
            t["classifier"] = got
            t["kept"] = got == t["orders"]
            n += len(got)
            agree += sum(a == b for a, b in zip(got, t["orders"]))
        kept = sum(t["kept"] for t in items)
        print(f"  {label}: {len(items)} items, {n} pieces; read as labelled {agree} ({100 * agree / max(n, 1):.1f}%); kept {kept} ({100 * kept / max(len(items), 1):.1f}%)")
    for t in new:
        if not t["kept"]:
            print(f"    left out {t['id']}: {t['line']!r} -> {t['pieces']} labelled {t['orders']}, read {t['classifier']}")
    json.dump(old + new, io.open(CHECKED, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"wrote {CHECKED}")


def training():
    """chains3_v55.training(pieces4d_final) with the v57 data, the v58 context items, and the v58 items as heard."""
    rows = build_v57.training_set(build_v57.LINES, build_v57.SEEDS)
    import make_spec_v55
    fragments = {t for v in make_spec_v55.FRAGMENTS_TO.values() for t in v}   # as pieces4d_final: "to this wall" seeds out
    rows = [r for r in rows if not (r["id"].startswith("seed_") or "|seed_" in r["id"]) or r["text"].strip().lower() not in fragments]
    singles = [r for r in rows if not C.has_then(r["text"])]
    pool = [r for r in singles if C.part_ok(r)]
    out = [{"text": r["text"], "pieces": [r["text"]]} for r in singles]
    out += [{"text": r["text"], "pieces": r["pieces"]} for r in C2.compose(pool, C.JOIN_TRAIN + C2.JOIN4, C.N_COMPOSED, random.Random(1002), "c",
                                                                          sizes=((2, 0.55), (3, 0.30), (4, 0.15)))]
    kept, heard = C2.teacher()
    out += C2.TYPED_COPIES * [{"text": t["text"], "pieces": t["pieces"]} for t in kept]
    n_heard = 0
    for cond in C2.VOICES[ROWS_OF]:
        got = [{"text": heard[cond][t["id"]], "pieces": t["pieces"]} for t in kept if heard.get(cond, {}).get(t["id"], "").strip()]
        n_heard += len(got)
        out += got
    ctx = context_kept()
    bots = sorted({x["bot"] for x in ctx if x["bot"]})
    rng = random.Random(3001)
    res = []
    for r in out:
        before, bot = [], None
        if rng.random() < P_CONTEXT:
            n = rng.choices([k for k, _ in N_BEFORE], [w for _, w in N_BEFORE])[0]
            before = [rng.choice(pool)["text"] for _ in range(n)]
            if bots and rng.random() < C2.P_BOT:
                bot = rng.choice(bots)
        res.append({"text": C2.turn(before, bot, r["text"]), "answer": "\n".join(r["pieces"])})
    crng = random.Random(3002)
    copies = lambda x: V58_COPIES if x["id"].startswith("x58_") else V55_COPIES if x["id"].startswith("x55_") else C2.CTX_COPIES  # noqa: E731
    for copy in range(max(C2.CTX_COPIES, V55_COPIES, V58_COPIES)):
        for x in ctx:
            if copy >= copies(x):
                continue
            n = min(crng.choices([k for k, _ in CTX_EXTRA], [w for _, w in CTX_EXTRA])[0], 5 - len(x["before"]))
            older = [crng.choice(pool)["text"] for _ in range(max(0, n))]
            res.append({"text": C2.turn(older + x["before"], x["bot"], x["line"]), "answer": "\n".join(x["pieces"])})
    old_ctx = [x for x in ctx if not x["id"].startswith("x58_")]
    new_ctx = [x for x in ctx if x["id"].startswith("x58_")]
    got = [{"text": C2.turn(before, x["bot"], line), "answer": "\n".join(x["pieces"])} for x, before, line, _ in C2.context_heard(old_ctx, C2.VOICES[ROWS_OF])]
    got_new = [{"text": C2.turn(before, x["bot"], line), "answer": "\n".join(x["pieces"])}
               for x, before, line, _ in C2.context_heard(new_ctx, C2.VOICES[ROWS_OF], HEARD_V58)] if os.path.exists(HEARD_V58) else []
    res += got + got_new
    counts = {"singles": len(singles), "composed": C.N_COMPOSED, "teacher": len(kept), "teacher_heard": n_heard, "context": len(ctx),
              "context_v58": len(new_ctx), "context_heard": len(got), "context_v58_heard": len(got_new)}
    return res, counts


def train(seed=0):
    t0 = time.time()
    rows, counts = training()
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=C2.SYSTEM["pieces"], checkpoint=True)
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": C2.SYSTEM["pieces"], "p_context": P_CONTEXT, "n_before": N_BEFORE, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1)
    print(f"chains4 {VARIANT} seed {seed}: {counts}, {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    C2.answers(model, turns, VARIANT, seed, extra)


def gguf(seed=0):
    """gguf_v54.py make on this round's adapter: merged into its base, converted, quantized -> models/gguf/pieces5_final_s0-Q4_K_M.gguf"""
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    """export_chain_cpp.py for the game: models/coop-chain-v58/cpp with this round's decoder and round four's router (v55).
    The v58 router (router_v58.py) was trained and is kept in models/coop-router-deberta-v3-small-v58, but it routed worse than
    v55's on round three's blind sets (1 to 3 points on each) and on the owner's lines ("Step up here and find cover." 0.19,
    "jump up and shoot that wall." 0.47, "Now this." 0.48: the decoder never saw them); the owner chose decoder v58 with
    classifier v58 (2026-10-18)."""
    sys.argv = [sys.argv[0], VARIANT, str(seed)]     # the exporter reads its variant from the command line when it loads
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v58", "cpp")
    E.ROUTER = os.path.join(E.MODELS, "coop-router-deberta-v3-small-v55")
    E.main()


REPEAT_LINE = re.compile(r"^\W*(?:(?:uh|um|ok|okay|so|and|yeah|nah|no)\W+)*(?:try (?:that |it |this )?again|again|do (?:that|it|this) again|"
                         r"(?:one more|once more)(?: time)?|same again|more|repeat(?: that)?)\W*(?:please)?\W*$", re.I)
NEGATED = re.compile(r"^\W*(?:(?:no|nah|ok|okay|hey)\W+)*(?:don'?t|do not|never)\b", re.I)


def score():
    """Round three's blind sets (aggregates only) answered by round four's game decoder (pieces4d_final) and by this round's,
    every piece read by the v57 ensemble -> chains4_58_score.log; each number on every item and on the items neither the repeat
    nor the negation rule touches (round three's labels read those otherwise)."""
    ts = C2.tests()
    files = [("pieces4d_final (round 4, the game's)", os.path.join(HERE, "chains3_55_pieces4d_final_s0.json"), "router55_final_small_s0.json")]
    files += [(f[len("chains4_58_"):-len("_s0.json")], os.path.join(HERE, f), "router58_final_small_s0.json")
              for f in sorted(os.listdir(HERE)) if f.startswith("chains4_58_pieces") and f.endswith("_s0.json")]
    preds = {name: C2.jload(path)["pred"] for name, path, _ in files}
    routers = {name: C2.jload(HERE, r)["probs"] for name, _, r in files}
    sets = ("blind2", "blind2_heard3", "ctx", "ctx_heard3")
    texts = {build_v57.norm(t["text"]) for s in sets for t in ts[s]}
    for pred in preds.values():
        texts |= {build_v57.norm(p) for s in sets for a in pred[s].values() for p in C2.split(a)}
    texts = sorted(t for t in texts if t)
    got, _ = C.bot_picks([{"id": str(n), "text": t} for n, t in enumerate(texts)])
    picks = {t: [got[str(n)][0]] for n, t in enumerate(texts)}
    touched = lambda t: bool(REPEAT_LINE.match(t["text"]) or NEGATED.match(t["text"]))  # noqa: E731

    def right(s, t, pieces):
        intents = C2.orders_of(pieces, picks) == t["orders"]
        if not s.startswith("ctx"):
            return intents
        return intents and (t["places"] is None or [C2.place(p) for p in pieces] == [tuple(x) if x is not None else None for x in t["places"]])

    out = io.StringIO()
    names = [name for name, _, _ in files]
    print(f"{'':58s}" + "".join(f"{n[:24]:>26s}" for n in names), file=out)
    for s, label in (("blind2", "chains, typed"), ("blind2_heard3", "chains, three unseen voices"), ("ctx", "context, typed (intents and places)"),
                     ("ctx_heard3", "context, three unseen voices")):
        rows = [t for t in ts[s] if t.get("orders")]
        keep = [t for t in rows if not touched(t)]
        for sub, what in ((rows, f"{label}: all {len(rows)}"), (keep, f"  without the {len(rows) - len(keep)} repeats and negations")):
            for wired in (False, True):
                cells = []
                for name in names:
                    pred, pr = preds[name], routers[name]
                    hit = sum(right(s, t, C2.split(pred[s][t["id"]]) if not wired or pr[s][t["id"]] >= 0.5 else [t["text"]]) for t in sub)
                    cells.append(f"{100 * hit / max(len(sub), 1):26.1f}")
                print(f"{what + (', through the router' if wired else ''):58s}" + "".join(cells), file=out)
    print(out.getvalue(), end="")
    io.open(os.path.join(HERE, "chains4_58_score.log"), "w", encoding="utf-8").write(out.getvalue())


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "score":
        score()
    elif what == "check":
        check()
    elif what == "train":
        train(seed)
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    else:
        print(__doc__)
