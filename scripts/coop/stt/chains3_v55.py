"""Round four of the chains study (bot v55, 2026-10-14): the game's rewriter trained again after the owner's play.
What changes against round three's pieces3_final (chains2_v54.py), and why:
  - the labels are v55's (44 intents) and the calculator is the v55 ensemble: a piece is kept when it reads as labelled;
  - spec_context_v55.json: a bare repeat ("try again", "more", "again") is written back as it is (REPEAT: the game knows
    what failed), a fragment with a pointing word completes the last order and keeps the word ("to this wall" after
    "start shooting" -> "shoot at this wall"), a pointing answer to "Which ...?" is the asked order there, a negated order
    is written back as it is (WAIT). The context items of rounds two and three that rewrote a repeat into the earlier
    order are changed to the line as it is; their negated orders read WAIT. New items: chains2/ctx_teacher_v55_*.json
    (three AI teachers, 60 each);
  - the owner keeps five earlier lines (chain_config.json "memory_lines" 5, 2026-10-14); round three only ever showed the
    decoder one or two. The unrelated earlier lines put in front of half of the rows are now one to five.
Everything else is round three's recipe on every line (Qwen3-1.7B, QLoRA r16, three epochs, the teacher lines typed twice
and heard from four voices, the context items three times and as heard).

    python chains3_v55.py check     the context items (old, changed; new) read by the v55 ensemble -> chains2/ctx_checked_v55.json
    python chains3_v55.py train     pieces4_final seed 0 -> models/coop-qwen3-qlora-chains3-v55/pieces4_final_seed0, and its
                                    answers on round three's test sets -> chains3_55_pieces4_final_s0.json
    python chains3_v55.py gguf      the adapter merged, as GGUF in 4 bits (gguf_v54.py make)
    python chains3_v55.py export    models/coop-chain-v55/cpp for the engine (export_chain_cpp.py; router_v55.py first)
    python chains3_v55.py score     round three's blind sets, round three's game decoder against every variant here -> chains3_55_score.log
The variant is CHAINS3_VARIANT (pieces4_final, pieces4b_final, pieces4c_final, pieces4d_final; the default is the game's).
"""
import io, json, os, random, re, sys, time
os.environ["COOP_TAG"] = "v55"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, COOP)
import coop_v2 as V                    # the v55 vocabulary, imported first: the scripts below set COOP_TAG=v54 when they load
import build_v55
sys.modules["build_v54"] = build_v55   # they import build_v54 by name; they get the v55 lines and seeds
import torch
import qlora_v54 as Q
import chains_v54 as C
import chains2_v54 as C2
import coop_bot
assert V.TAG == "v55" and len(V.INTENTS) == 44, (V.TAG, len(V.INTENTS))

C.BOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v55"))   # the calculator
# pieces4_final: the first decoder of this round. memory_lines_probe.py (CHAIN=models/coop-chain-v55/cpp) showed it more
# easily led by older lines than round three's: with five earlier lines in front, 9 of the 54 items with a context of their
# own changed (round three: 0), and with their own context alone it took "Brown ones." after "Smoke the main door. / Go to the
# stairs." as smoke. Its rows had unrelated earlier lines only in front of lines with no context of their own; a context
# item never had older lines before its own. pieces4b_final (after tuning, the same day): every context item also with
# older unrelated lines in front of its own (CTX_EXTRA), so that the line that matters is the last one, not the only one.
# pieces4b_final kept to the last line with older ones in front (memory_lines_probe) but lost the fragments: of ten pointing
# fragments after an order ("To this wall." after "Start shooting.") it completed 5, pieces4_final 8. pieces4c_final (after
# tuning, the same day): pieces4b's rows with the v55 teachers' items (ctx_teacher_v55_*: the fragments, the pointing
# answers, the repeats, the negations) in V55_COPIES copies instead of three
# pieces4c_final scored 20 of 24 on the owner's episodes and ten fragments, and still wrote "To this wall." after "Start
# shooting." back as it is, like pieces4b. Both were trained after make_spec_v55.py's twelve FRAGMENTS_TO seeds ("to this
# wall" MOVE_TO, for the classifier's reading of the line alone) joined the singles, half of which get unrelated earlier
# lines in front and are written back as they are: that taught the decoder to leave "to this wall" alone after any order.
# pieces4d_final (after tuning): pieces4c's rows without those twelve seeds among the decoder's singles. It scored 21 of 24
# (both of the owner's "To this wall." completed), and with five earlier lines none of the 54 items with a context of their own
# changed. The game's decoder. On round three's blind sets (score, chains3_55_score.log) it loses to round three's decoder on
# typed lines with a context alone (83.6 against 92.5) and is level with it through the router.
VARIANT, ROWS_OF = os.environ.get("CHAINS3_VARIANT", "pieces4d_final"), "pieces3"
V55_COPIES = 6 if VARIANT in ("pieces4c_final", "pieces4d_final") else 3
CTX_EXTRA = ((0, 0.4), (1, 0.25), (2, 0.2), (3, 0.15))     # per copy of a context item, at most five earlier lines in all
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = ROWS_OF
ADAPTER = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-qwen3-qlora-chains3-v55"))
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}")
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains3_55_{variant}_s{seed}.json")
CHECKED = os.path.join(C2.CH2, "ctx_checked_v55.json")
REPEAT_LINE = re.compile(r"^\W*(?:(?:uh|um|ok|okay|so|and|yeah|nah|no)\W+)*(?:try (?:that |it |this )?again|again|do (?:that|it|this) again|"
                         r"(?:one more|once more)(?: time)?|same again|more|repeat(?: that)?)\W*(?:please)?\W*$", re.I)
# fixed before training: how many unrelated earlier lines go in front of a row that has none of its own
P_CONTEXT, N_BEFORE = 0.5, ((1, 0.35), (2, 0.25), (3, 0.15), (4, 0.12), (5, 0.13))


def v55_context():
    """Rounds two and three's kept context items under spec_context_v55, then the v55 teachers' items."""
    old = [dict(x) for x in C2.jload(C2.CH2, "ctx_checked.json") if x["kept"]]
    changed = {"repeat": 0, "negated": 0}
    for x in old:
        if REPEAT_LINE.match(x["line"]) and x["pieces"] != [x["line"]]:
            x["pieces"], x["orders"] = [x["line"]], ["REPEAT"]
            changed["repeat"] += 1
        for k, (p, o) in enumerate(zip(x["pieces"], x["orders"])):
            if o == "NONE" and coop_bot.NEGATION.search(p):
                x["orders"][k] = "WAIT"
                changed["negated"] += 1
    new = []
    for v in ("r6", "cs", "stt"):
        new += C2.jload(C2.CH2, f"ctx_teacher_v55_{v}.json")
    return old, new, changed


def context_kept():
    """The context items of round four that the calculator kept (chains2/ctx_checked_v55.json)."""
    return [x for x in C2.jload(CHECKED) if x["kept"]]


def check():
    old, new, changed = v55_context()
    print(f"rounds two and three: {len(old)} kept items; changed under spec_context_v55: {changed}")
    picks, cfg = C.bot_picks([{"id": f"{t['id']}#{k}", "text": p} for t in old + new for k, p in enumerate(t["pieces"])])
    print(f"calculator: {C.BOT} (gate {cfg['gate']}, threshold {cfg['threshold']})")
    for label, items in (("old items", old), ("v55 items", new)):
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
    json.dump(old + new, io.open(CHECKED, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"wrote {CHECKED}")


def training():
    """chains2_v54.training(pieces3_final) with the v55 data, the v55 context items and one to five earlier lines."""
    rows = build_v55.training_set(build_v55.LINES, build_v55.SEEDS)
    if VARIANT == "pieces4d_final":
        import make_spec_v55
        fragments = {t for v in make_spec_v55.FRAGMENTS_TO.values() for t in v}
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
    ctx = [x for x in C2.jload(CHECKED) if x["kept"]]
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
    if VARIANT == "pieces4_final":
        res += C2.CTX_COPIES * [{"text": C2.turn(x["before"], x["bot"], x["line"]), "answer": "\n".join(x["pieces"])} for x in ctx]
    else:
        crng = random.Random(3002)
        for copy in range(max(C2.CTX_COPIES, V55_COPIES)):
            for x in ctx:
                if copy >= (V55_COPIES if x["id"].startswith("x55_") else C2.CTX_COPIES):
                    continue
                n = min(crng.choices([k for k, _ in CTX_EXTRA], [w for _, w in CTX_EXTRA])[0], 5 - len(x["before"]))
                older = [crng.choice(pool)["text"] for _ in range(max(0, n))]
                res.append({"text": C2.turn(older + x["before"], x["bot"], x["line"]), "answer": "\n".join(x["pieces"])})
    got = [{"text": C2.turn(before, x["bot"], line), "answer": "\n".join(x["pieces"])} for x, before, line, _ in C2.context_heard(ctx, C2.VOICES[ROWS_OF])]
    res += got
    counts = {"singles": len(singles), "composed": C.N_COMPOSED, "teacher": len(kept), "teacher_heard": n_heard, "context": len(ctx),
              "context_heard": len(got)}
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
    print(f"chains3 {VARIANT} seed {seed}: {counts}, {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    C2.answers(model, turns, VARIANT, seed, extra)


def gguf(seed=0):
    """gguf_v54.py make on this round's adapter: merged into its base, converted, quantized -> models/gguf/pieces4_final_s0-Q4_K_M.gguf"""
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    """export_chain_cpp.py for the game: models/coop-chain-v55/cpp with the v55 router (router_v55.py) and this round's decoder."""
    sys.argv = [sys.argv[0], VARIANT, str(seed)]     # the exporter reads its variant from the command line when it loads
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, "coop-chain-v55", "cpp")
    E.ROUTER = os.path.join(E.MODELS, "coop-router-deberta-v3-small-v55")
    E.main()


NEGATED = re.compile(r"^\W*(?:(?:no|nah|ok|okay|hey)\W+)*(?:don'?t|do not|never)\b", re.I)


def score():
    """Round three's blind sets (chains2_v54.py tests(); aggregates only) answered by round three's game decoder and by each
    round-four variant, every piece read by the v55 ensemble -> chains3_55_score.log. The sets were labelled under round
    three's spec: a bare repeat there is the earlier order and a negated order NONE or NO, where round four writes both
    back as they are (REPEAT, WAIT). So each number is given twice: on every item, and on the items neither rule touches."""
    ts = C2.tests()
    files = [("pieces3_final (round 3)", os.path.join(HERE, "chains2_54_pieces3_final_s0.json"), "router54_final_small_s0.json")]
    files += [(f[len("chains3_55_"):-len("_s0.json")], os.path.join(HERE, f), "router55_final_small_s0.json")
              for f in sorted(os.listdir(HERE)) if f.startswith("chains3_55_pieces") and f.endswith("_s0.json")]
    preds = {name: C2.jload(path)["pred"] for name, path, _ in files}
    routers = {name: C2.jload(HERE, r)["probs"] for name, _, r in files}
    sets = ("blind2", "blind2_heard3", "ctx", "ctx_heard3")
    texts = {build_v55.norm(t["text"]) for s in sets for t in ts[s]}
    for pred in preds.values():
        texts |= {build_v55.norm(p) for s in sets for a in pred[s].values() for p in C2.split(a)}
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
    io.open(os.path.join(HERE, "chains3_55_score.log"), "w", encoding="utf-8").write(out.getvalue())


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
