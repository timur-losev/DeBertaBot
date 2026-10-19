"""Round six of the chains study (chain v59 over bot v58, 2026-10-18): the game's rewriter trained again after the owner's play
with bot v58 and chain v58. Why: "Go up by these stairs and jump up." (and "... jump down", "... sit down", "... find cover",
"Move up and check.", "Go up and check there.") made one order of a movement and another action, so the bot went up and never
jumped, sat or hid; and in context.txt, after "shoot", "shoot here", "go there", decoder v58 wrote the correction "no, here, on
my pin" as a shot at the pin (decoder v55: "go to my pin"). What changes against round five's pieces5_final (chains4_v58.py):
  - the labels are v58's (the same 47 intents) and the calculator is the v58 ensemble: a piece is kept when it reads as labelled;
  - spec_context_v59.json: rules 9 (a movement with its own way or place, then another action, is two orders; the exceptions of
    spec_chain.json's rule 3 stay one) and 3b (a correction is for the LAST order). New items: chains2/ctx_teacher_v59_*.json
    (three AI authors, 40 each, blind to the owner's lines and to the earlier items), in V59_COPIES copies with older lines in
    front, and the r6 and cs ones also as heard from four voices (chains2/ctx_teacher_v59_heard.json);
  - the owner's lines are a test set only (chains2/owner_ctx_v59.json: round five's 30 and 20 of a movement and another order),
    never trained on.
Everything else is round five's recipe (Qwen3-1.7B, QLoRA r16, three epochs, the rows of pieces5_final).

    python chains5_v59.py check     every context item (round five's kept ones, the v59 ones) read by the v58 ensemble -> chains2/ctx_checked_v59.json
    python chains5_v59.py train     pieces6_final seed 0 -> models/coop-qwen3-qlora-chains5-v59/pieces6_final_seed0, and its answers
                                    on round three's test sets -> chains5_59_pieces6_final_s0.json
    python chains5_v59.py gguf      the adapter merged, as GGUF in 4 bits (gguf_v54.py make)
    python chains5_v59.py export    models/coop-chain-v59/cpp for the engine (export_chain_cpp.py) with router v59 (router_v59.py),
                                    the owner's choice; CHAINS5_ROUTER=<models folder> exports another one
    python chains5_v59.py score     round three's blind sets: round five's game decoder against this round's, with router v55 and
                                    with router v59 (router_v59.py) -> chains5_59_score.log
The owner's set: OWNER_CTX_SET=chains2/owner_ctx_v59.json python owner_ctx_score.py <coop_cli.exe> <bot cpp> <chain cpp>.
"""
import io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v58"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, COOP)
import coop_v2 as V                    # the v58 vocabulary, imported first: the scripts below set COOP_TAG=v54 when they load
import build_v58
sys.modules["build_v54"] = build_v58   # they import build_v54 by name; they get the v58 lines and seeds
import torch
import qlora_v54 as Q
import chains_v54 as C
import chains2_v54 as C2
import coop_bot
assert V.TAG == "v58" and len(V.INTENTS) == 47, (V.TAG, len(V.INTENTS))

MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
C.BOT = os.path.join(MODELS, "coop-deberta-v3-ens3-v58")   # the calculator
VARIANT, ROWS_OF = os.environ.get("CHAINS5_VARIANT", "pieces6_final"), "pieces3"
V55_COPIES = V58_COPIES = V59_COPIES = 6   # as round five's
CTX_EXTRA = ((0, 0.4), (1, 0.25), (2, 0.2), (3, 0.15))     # per copy of a context item, at most five earlier lines in all
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = ROWS_OF
ADAPTER = os.path.join(MODELS, "coop-qwen3-qlora-chains5-v59")
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}")
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains5_59_{variant}_s{seed}.json")
CHECKED_V58 = os.path.join(C2.CH2, "ctx_checked_v58.json")
CHECKED = os.path.join(C2.CH2, "ctx_checked_v59.json")
HEARD_V58 = os.path.join(C2.CH2, "ctx_teacher_v58_heard.json")
HEARD_V59 = os.path.join(C2.CH2, "ctx_teacher_v59_heard.json")
AUTHORS = ("r6", "cs", "stt")
# fixed before training, as rounds four and five: how many unrelated earlier lines go in front of a row that has none of its own
P_CONTEXT, N_BEFORE = 0.5, ((1, 0.35), (2, 0.25), (3, 0.15), (4, 0.12), (5, 0.13))

# The authors' files stay as they wrote them; what is mended is here: id -> (pieces, orders), or None (out). The stt author was
# told (by the developer, wrongly) to write the pieces with the recognizer's slips mended; rule 11 of spec_context_v55.json keeps
# what the recognizer made of a word as heard, and nothing downstream knows these four words ("pistil", "prawn", "my pen",
# "frack": the place matcher and the game's weapon reader do not), so a piece with the heard word helps nobody and one with the
# word mended would teach the decoder to guess words: the four are out.
CURATE = {"x59_stt_004": None, "x59_stt_005": None, "x59_stt_009": None, "x59_stt_017": None}
# Round five's items of a bare going-on written back as it is ("Keep moving." with nothing before it that moved the bot) were
# labelled NONE; the v58 classifier reads them MOVE_TO with no place, the owner's choice (2026-10-18: "Идти куда я смотрю"):
# the same pieces under the label the bot now gives them.
OLD_RELABEL = {"x58_r6_017": ["MOVE_TO"], "x58_cs_053": ["MOVE_TO"], "x58_stt_053": ["MOVE_TO"]}


def v59_context():
    """Round five's kept context items (round four's and the v58 ones), then the v59 authors' items as CURATE mends them."""
    old = [dict(x) for x in C2.jload(CHECKED_V58) if x["kept"]]
    for x in old:
        if x["id"] in OLD_RELABEL:
            assert x["pieces"] == [x["line"]] and x["orders"] == ["NONE"], x["id"]
            x["orders"] = OLD_RELABEL[x["id"]]
    new = []
    for v in AUTHORS:
        for x in C2.jload(C2.CH2, f"ctx_teacher_v59_{v}.json"):
            if x["id"] in CURATE:
                if CURATE[x["id"]] is None:
                    continue
                x = dict(x, pieces=CURATE[x["id"]][0], orders=CURATE[x["id"]][1], curated=True)
            new.append(x)
    return old, new


def context_kept():
    """The context items of round six that the calculator kept (chains2/ctx_checked_v59.json)."""
    return [x for x in C2.jload(CHECKED) if x["kept"]]


def check():
    old, new = v59_context()
    picks, cfg = C.bot_picks([{"id": f"{t['id']}#{k}", "text": p} for t in old + new for k, p in enumerate(t["pieces"])])
    print(f"calculator: {C.BOT} (gate {cfg['gate']}, threshold {cfg['threshold']})")
    for label, items in (("round five's items", old), ("v59 items", new)):
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
    for t in old + new:
        if not t["kept"]:
            print(f"    left out {t['id']}: {t['line']!r} -> {t['pieces']} labelled {t['orders']}, read {t['classifier']}")
    json.dump(old + new, io.open(CHECKED, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"wrote {CHECKED}")


def training():
    """chains4_v58.training (pieces5_final) with the v58 data, the v59 context items, and the v58 and v59 items as heard."""
    rows = build_v58.training_set(build_v58.LINES, build_v58.SEEDS)
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
    copies = lambda x: (V59_COPIES if x["id"].startswith("x59_") else V58_COPIES if x["id"].startswith("x58_")   # noqa: E731
                        else V55_COPIES if x["id"].startswith("x55_") else C2.CTX_COPIES)
    for copy in range(max(C2.CTX_COPIES, V55_COPIES, V58_COPIES, V59_COPIES)):
        for x in ctx:
            if copy >= copies(x):
                continue
            n = min(crng.choices([k for k, _ in CTX_EXTRA], [w for _, w in CTX_EXTRA])[0], 5 - len(x["before"]))
            older = [crng.choice(pool)["text"] for _ in range(max(0, n))]
            res.append({"text": C2.turn(older + x["before"], x["bot"], x["line"]), "answer": "\n".join(x["pieces"])})
    old_ctx = [x for x in ctx if not x["id"].startswith(("x58_", "x59_"))]
    v58_ctx = [x for x in ctx if x["id"].startswith("x58_")]
    v59_ctx = [x for x in ctx if x["id"].startswith("x59_")]
    got = [{"text": C2.turn(before, x["bot"], line), "answer": "\n".join(x["pieces"])} for x, before, line, _ in C2.context_heard(old_ctx, C2.VOICES[ROWS_OF])]
    got58 = [{"text": C2.turn(before, x["bot"], line), "answer": "\n".join(x["pieces"])}
             for x, before, line, _ in C2.context_heard(v58_ctx, C2.VOICES[ROWS_OF], HEARD_V58)] if os.path.exists(HEARD_V58) else []
    got59 = [{"text": C2.turn(before, x["bot"], line), "answer": "\n".join(x["pieces"])}
             for x, before, line, _ in C2.context_heard(v59_ctx, C2.VOICES[ROWS_OF], HEARD_V59)] if os.path.exists(HEARD_V59) else []
    res += got + got58 + got59
    counts = {"singles": len(singles), "composed": C.N_COMPOSED, "teacher": len(kept), "teacher_heard": n_heard, "context": len(ctx),
              "context_v58": len(v58_ctx), "context_v59": len(v59_ctx), "context_heard": len(got), "context_v58_heard": len(got58),
              "context_v59_heard": len(got59)}
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
    print(f"chains5 {VARIANT} seed {seed}: {counts}, {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    C2.answers(model, turns, VARIANT, seed, extra)


def gguf(seed=0):
    """gguf_v54.py make on this round's adapter: merged into its base, converted, quantized -> models/gguf/pieces6_final_s0-Q4_K_M.gguf"""
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    """export_chain_cpp.py for the game: models/coop-chain-v59/cpp with this round's decoder and router v59. With round four's
    router v55 the owner's 50 lines read 38/50, with v59 45/50 (all of "go up by these stairs and jump up / sit down / find
    cover" go to the decoder); on round three's blind chains v59 routes 3 of 150 worse. The owner chose v59 (2026-10-18)."""
    sys.argv = [sys.argv[0], VARIANT, str(seed)]     # the exporter reads its variant from the command line when it loads
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v59", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS5_ROUTER", "coop-router-deberta-v3-small-v59"))
    print(f"router: {E.ROUTER}")
    E.main()


REPEAT_LINE = re.compile(r"^\W*(?:(?:uh|um|ok|okay|so|and|yeah|nah|no)\W+)*(?:try (?:that |it |this )?again|again|do (?:that|it|this) again|"
                         r"(?:one more|once more)(?: time)?|same again|more|repeat(?: that)?)\W*(?:please)?\W*$", re.I)
NEGATED = re.compile(r"^\W*(?:(?:no|nah|ok|okay|hey)\W+)*(?:don'?t|do not|never)\b", re.I)


def score():
    """Round three's blind sets (aggregates only) answered by round five's game decoder (with router v55, as shipped) and by
    this round's, with router v55 and with router v59, every piece read by the v58 ensemble -> chains5_59_score.log; each number on
    every item and on the items neither the repeat nor the negation rule touches (round three's labels read those otherwise)."""
    ts = C2.tests()
    files = [("round 5, router v55 (the game's)", os.path.join(HERE, "chains4_58_pieces5_final_s0.json"), "router55_final_small_s0.json")]
    mine = os.path.join(HERE, f"chains5_59_{VARIANT}_s0.json")
    files.append((f"{VARIANT}, router v55", mine, "router55_final_small_s0.json"))
    if os.path.exists(os.path.join(HERE, "router59_final_small_s0.json")):
        files.append((f"{VARIANT}, router v59", mine, "router59_final_small_s0.json"))
    preds = {name: C2.jload(path)["pred"] for name, path, _ in files}
    routers = {name: C2.jload(HERE, r)["probs"] for name, _, r in files}
    sets = ("blind2", "blind2_heard3", "ctx", "ctx_heard3")
    texts = {build_v58.norm(t["text"]) for s in sets for t in ts[s]}
    for pred in preds.values():
        texts |= {build_v58.norm(p) for s in sets for a in pred[s].values() for p in C2.split(a)}
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
    print(f"{'':58s}" + "".join(f"{n[:30]:>32s}" for n in names), file=out)
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
                    cells.append(f"{100 * hit / max(len(sub), 1):32.1f}")
                print(f"{what + (', through the router' if wired else ''):58s}" + "".join(cells), file=out)
    print(out.getvalue(), end="")
    io.open(os.path.join(HERE, "chains5_59_score.log"), "w", encoding="utf-8").write(out.getvalue())


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
