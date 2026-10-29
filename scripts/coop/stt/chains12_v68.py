"""Round v68 of the chains study (2026-10-29): decoder v68s. The owner: «добавляй строки и стартуй обучение» (the timer rows
and the new things, chains2/ml_v68/TODO_v68.md items 1 and 3).

What changes against v67s (chains11_v67.py ... short):
  - the rows of the rounds before (chains10_v66.training()) as place vocabulary v15 reads them: bot v60's farm rows wrote
    «грядка» / «bancal» as "bed", the bed to sleep on since v14; make_combos_v68.old_rows_v15 writes "garden bed" there
    (150 rows; the rows about a bed to sleep on stay);
  - v67's generator on round v68's lexicon (make_combos_v68.decoder_rows: the bed, the garden bed, the rock of vocabulary v15)
    in place of v67's rows: the same frames, the same counts, a third of the rows without a scene given one that changes nothing;
  - the timer rows (make_time_v68.time_rows: "for N seconds", "in N seconds <order>", "for a few seconds", "for A to B
    seconds", "for N more seconds", the idioms with no time; every row checked by time_phrase.find), the same share of
    neutral scenes;
  - rows equal to an item of a held-out test (chains2/ml_v67/test_v67.json, chains2/ml_v68/test_v68_time.json, both written
    blind) are dropped;
  - v67s's short system turn, a new LoRA on plain Qwen3-1.7B, v66's recipe (r16, 3 epochs); trained alone on the GPU (the
    classifier needs no round: the time is cut from the line before it, and it learns no place names).

    python chains12_v68.py data       the rows, counted, with samples
    python chains12_v68.py train      -> models/coop-qwen3-qlora-chains12-v68/pieces13v68s_final_seed0; answers on the test sets
    python chains12_v68.py gguf | export
"""
import io, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_argv = sys.argv
sys.argv = sys.argv[:3]                 # chains11_v67 reads a "short" of its own from argv[3]
import chains11_v67 as P11              # v67's machinery (and through it v66's rows and helpers)
sys.argv = _argv
from chains11_v67 import P10, P9, P, C, C2, Q, P8, torch
ML68 = os.path.join(C2.CH2, "ml_v68")
sys.path.insert(0, ML68)
import make_combos_v68 as M68           # sets the v67 generator's lexicon to v68's
import make_time_v68 as T68
MC = M68.MC

SYSTEM = P11.SYSTEM_V67S
# V68_RUN: "" for the first run (v68s, trained 2026-10-29 01:51-04:33), "2" for v68s2 (the idioms "wait a moment", not
# "just a moment": make_time_v68.IDIOMS); each run has its own adapter, answers, gguf and export
TAG = "v68s" + os.environ.get("V68_RUN", "")
VARIANT = f"pieces13{TAG}_final"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = P.ROWS_OF
ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains12-v68")
_adapter = C2.adapter_dir
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}") if variant == VARIANT else _adapter(variant, seed)
_out = C2.out_path
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains12_68_{variant}_s{seed}.json") if variant == VARIANT else _out(variant, seed)
NEUTRAL_SCENE = P11.NEUTRAL_SCENE
TIME_TEST = os.environ.get("V68_TIME_TEST") or os.path.join(ML68, "test_v68_time.json")    # the variable: a dry run only


def test_keys():
    """The held-out tests' items as (lines before, scene, line), normalised: v67's and the timer test."""
    keys = P11.test_keys()
    items = json.load(io.open(TIME_TEST, encoding="utf-8"))["items"]
    keys |= {P10.key_of([P10.norm(b) for b in it.get("before", [])], (it.get("scene") or "").strip().lower(), P10.norm(it["line"]))
             for it in items}
    return keys, len(items)


def with_neutral_scenes(rows, rng):
    for r in rows:
        if "scene: " not in r["text"] and r["case"] not in ("multi", "time_multi") and rng.random() < NEUTRAL_SCENE:
            scene = P9.neutral_scene(r["text"], r["answer"], rng)
            if scene:
                r["text"] = P9.with_scene(r["text"], scene)
    return rows


def training():
    old, counts, split = P10.training()
    old, changed = M68.old_rows_v15(old)
    new = with_neutral_scenes(M68.decoder_rows(random.Random(6801)), random.Random(6802))
    timed = with_neutral_scenes(T68.time_rows(random.Random(6811)), random.Random(6812))
    held, n_time_test = test_keys()
    kept_new = [r for r in new if P10.row_key(r["text"]) not in held]
    kept_time = [r for r in timed if P10.row_key(r["text"]) not in held]
    by = {}
    for r in kept_new + kept_time:
        by[f"{r['case']}/{r['lang']}"] = by.get(f"{r['case']}/{r['lang']}", 0) + 1
    counts["v68"] = {"generated": by, "old_rows_garden_bed": changed, "time_test_items": n_time_test,
                     "dropped_as_test": len(new) + len(timed) - len(kept_new) - len(kept_time)}
    counts["v66_rows"], counts["v68_things_rows"], counts["v68_time_rows"] = len(old), len(kept_new), len(kept_time)
    rows = old + [{"text": r["text"], "answer": r["answer"]} for r in kept_new + kept_time]
    return rows, counts, split


def train(seed=0):
    t0 = time.time()
    rows, counts, split = training()
    # a snapshot every 30 minutes: the same command after a crash or a stop goes on from the last one
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=SYSTEM, checkpoint=True,
                           snapshot_dir=os.path.join(ADAPTER, f"{VARIANT}_seed{seed}_snapshot"))
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": SYSTEM, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"chains12 {VARIANT} seed {seed}: {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    model.eval()
    import measure_v67 as M7
    M7.gen(model, turns, os.path.join(HERE, f"measure_v67_answers_{TAG}.json"), TAG, C, C2)
    import measure_v66 as M6
    M6.gen(model, turns, os.path.join(HERE, f"measure_v66_answers_{TAG}.json"), TAG, C, C2)
    P9.scene_answers(model, turns, os.path.join(HERE, f"measure_v65_answers_{TAG}.json"))
    P8.test_answers(model, turns, os.path.join(HERE, f"chains12_68_test64_{VARIANT}_s{seed}.json"))
    C2.answers(model, turns, VARIANT, seed, extra)
    P.ml_answers(model, turns, os.path.join(HERE, f"chains12_68_ml_{VARIANT}_s{seed}.json"), extra)
    P8.P7.pairs_answers(model, turns, os.path.join(HERE, f"chains12_68_pairs_{VARIANT}_s{seed}.json"))


def gguf(seed=0):
    import gguf_v54 as G
    G.make(VARIANT, seed)


def export(seed=0):
    """As chains11_v67.export, to models/coop-chain-v68s/cpp (v67's chain tests: 40 lines with a scene, 20 with a failed one)."""
    sys.argv = [sys.argv[0], VARIANT, str(seed)]
    C2.SYSTEM["pieces"] = SYSTEM
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, f"coop-chain-{TAG}", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS12_ROUTER", "coop-router-deberta-v3-small-v63"))
    base = E.test_rows

    def rows():
        out = base()
        made, _ = P9.scene_rows(random.Random(6577))
        failed = [r for r in MC.failed_rows(random.Random(6779)) if r["case"] == "failed"]
        for x in random.Random(6578).sample(made, 40) + random.Random(6780).sample(failed, 20):
            lines = x["text"].split("\n")
            scene = next(t[len("scene: "):] for t in lines if t.startswith("scene: "))
            out.append({"before": [t[len("before: "):] for t in lines if t.startswith("before: ")], "bot": None,
                        "scene": scene, "scene_parts": P11.scene_parts_v67(scene), "line": lines[-1][len("now: "):]})
        return out
    E.test_rows = rows
    E.main()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts["v68"], ensure_ascii=False, indent=1))
        print(counts["v66_rows"], "+", counts["v68_things_rows"], "+", counts["v68_time_rows"], "=", len(rows), "rows")
        rng = random.Random(3)
        for r in rng.sample(rows[-counts["v68_time_rows"]:], 20) + rng.sample(rows[counts["v66_rows"]:-counts["v68_time_rows"]], 10):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        train(seed)
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    else:
        print(__doc__)
