"""Round v67 of the chains study (2026-10-27): decoder v67 on decoder v66's rows (chains10_v66.py). The owner: «Подготовь
обучение языковой модели версии 67, но я хочу, чтобы не было никаких ограничений, что можно сделать с чем. Предмет есть
предмет, и можно комбинировать». Plan: chains2/ml_v67/PLAN_v67.md; the generator: chains2/ml_v67/make_combos_v67.py.

What changes against v66 (its rows kept):
  - the generator's rows (make_combos_v67.decoder_rows): every intent's frames with any object of the lexicon in ru, es,
    en; a means at times, said in many ways and written at the end of the order as "using the <thing>"; a pronoun or a bare
    noun after the line that named the thing; the scene's "failed: <order>, <why>" and a short line with a thing ("поставь
    коробку") = that order using the thing; two orders in one line. A third of the rows with no scene get one that changes
    nothing (as v66's templates).
  - rows equal to an item of the held-out v67 test (chains2/ml_v67/test_v67.json, written blind) in lines before, scene
    and line are dropped (as v66).
  - the system turn says how a means is written and what a failed scene means (SYSTEM_V67). Plain Qwen3-1.7B, a new LoRA,
    v66's recipe (r16, 3 epochs).

    python chains11_v67.py data       the rows, counted, with samples
    python chains11_v67.py train      -> models/coop-qwen3-qlora-chains11-v67/pieces12v67_final_seed0; answers on every test set
    python chains11_v67.py gguf | export
"""
import io, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chains10_v66 as P10          # v66's rows (and through it v65's, v64's, ...)
from chains10_v66 import P9, P, C, C2, Q, P8, torch
ML67 = os.path.join(C2.CH2, "ml_v67")
sys.path.insert(0, ML67)
import make_combos_v67 as MC

SYSTEM_V67 = P10.SYSTEM_V66 + (" An order may say the thing it is done with: write it at the end of that order as \"using the <thing>\" "
                               "(\"climb onto the white table using the crate\"); any thing goes with any order. A scene part \"failed: "
                               "<order>, <why>\" is an order the bot could not carry out: a short line that now names a thing to use "
                               "(«поставь коробку», \"use the box\") is that order again using the thing.")
# The short system turn (the owner, 2026-10-28): the long one is 324 tokens in each of the 16 rows of a step, about nine tenths of
# the training's work, and it mostly says what the rows show. The same rows with this one train in about a fifth of the time;
# both are trained (this one first) and measured on every test, and the one that is not worse goes into the game.
#   python chains11_v67.py train|gguf|export 0 short
SYSTEM_V67S = "You are the AI teammate in a co-op shooter. Write what the player orders now in English, one order per line."
SHORT = sys.argv[3:4] == ["short"]
SYSTEM = SYSTEM_V67S if SHORT else SYSTEM_V67
TAG = "v67s" if SHORT else "v67"          # in the names of the answer files and of the exported chain
VARIANT = "pieces12v67s_final" if SHORT else "pieces12v67_final"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = P.ROWS_OF
ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains11-v67")
_adapter66 = C2.adapter_dir
C2.adapter_dir = lambda variant, seed: os.path.join(ADAPTER, f"{variant}_seed{seed}") if variant == VARIANT else _adapter66(variant, seed)
_out66 = C2.out_path
C2.out_path = lambda variant, seed: os.path.join(HERE, f"chains11_67_{variant}_s{seed}.json") if variant == VARIANT else _out66(variant, seed)
NEUTRAL_SCENE = 0.33


def test_keys():
    """The held-out v67 test's items as (lines before, scene, line), normalised: a generated row that is one of them is dropped."""
    return {P10.key_of([P10.norm(b) for b in it.get("before", [])], (it.get("scene") or "").strip().lower(), P10.norm(it["line"]))
            for it in P.jl(ML67, "test_v67.json")["items"]}


def training():
    rows, counts, split = P10.training()
    rng = random.Random(6701)
    new = MC.decoder_rows(rng)
    for r in new:
        if "scene: " not in r["text"] and r["case"] != "multi" and rng.random() < NEUTRAL_SCENE:
            scene = P9.neutral_scene(r["text"], r["answer"], rng)
            if scene:
                r["text"] = P9.with_scene(r["text"], scene)
    held = test_keys()
    kept = [r for r in new if P10.row_key(r["text"]) not in held]
    by = {}
    for r in kept:
        by[f"{r['case']}/{r['lang']}"] = by.get(f"{r['case']}/{r['lang']}", 0) + 1
    counts["v67"] = {"generated": by, "dropped_as_test": len(new) - len(kept)}
    counts["v66_rows"], counts["v67_rows"] = len(rows), len(kept)
    return rows + [{"text": r["text"], "answer": r["answer"]} for r in kept], counts, split


def train(seed=0):
    t0 = time.time()
    rows, counts, split = training()
    # a snapshot every 30 minutes (the owner, 2026-10-27): the same command after a crash or a stop goes on from the last one
    model, turns = Q.train(C.NAME, rows, seed, Q.TAGS["r16"], system=SYSTEM, checkpoint=True,
                           snapshot_dir=os.path.join(ADAPTER, f"{VARIANT}_seed{seed}_snapshot"))
    d = C2.adapter_dir(VARIANT, seed)
    os.makedirs(d, exist_ok=True)
    model.save_pretrained(d, safe_serialization=True)
    extra = {"rows": counts, "n_rows": len(rows), "train_s": round(time.time() - t0), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 1)}
    json.dump({"base": Q.MODELS[C.NAME], **Q.TAGS["r16"], "system": SYSTEM, **extra},
              io.open(os.path.join(d, "trained_on.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"chains11 {VARIANT} seed {seed}: {len(rows)} rows, trained in {time.time() - t0:.0f}s", flush=True)
    model.eval()
    import measure_v67 as M7
    M7.gen(model, turns, os.path.join(HERE, f"measure_v67_answers_{TAG}.json"), TAG, C, C2)
    import measure_v66 as M6
    M6.gen(model, turns, os.path.join(HERE, f"measure_v66_answers_{TAG}.json"), TAG, C, C2)
    P9.scene_answers(model, turns, os.path.join(HERE, f"measure_v65_answers_{TAG}.json"))
    P8.test_answers(model, turns, os.path.join(HERE, f"chains11_67_test64_{VARIANT}_s{seed}.json"))
    C2.answers(model, turns, VARIANT, seed, extra)
    P.ml_answers(model, turns, os.path.join(HERE, f"chains11_67_ml_{VARIANT}_s{seed}.json"), extra)
    P8.P7.pairs_answers(model, turns, os.path.join(HERE, f"chains11_67_pairs_{VARIANT}_s{seed}.json"))


def gguf(seed=0):
    import gguf_v54 as G
    G.make(VARIANT, seed)


def scene_parts_v67(scene):
    """chains9_v65.scene_parts with the failed part of decoder v67 ("failed: <order>, <why>", after the car's part)."""
    parts = scene.split("; ")
    failed = next((p[len("failed: "):] for p in parts if p.startswith("failed: ")), None)
    out = P9.scene_parts("; ".join(p for p in parts if not p.startswith("failed: ")))
    out["failed"] = failed
    return out


def export(seed=0):
    """As chains10_v66.export, to models/coop-chain-v67/cpp; the chain tests get 20 lines with a failed scene beside v66's 40
    with a scene (the C++ scene line against the server's)."""
    sys.argv = [sys.argv[0], VARIANT, str(seed)]
    C2.SYSTEM["pieces"] = SYSTEM
    import export_chain_cpp as E
    E.OUT = os.path.join(E.MODELS, f"coop-chain-{TAG}", "cpp")
    E.ROUTER = os.path.join(E.MODELS, os.environ.get("CHAINS11_ROUTER", "coop-router-deberta-v3-small-v63"))
    base = E.test_rows

    def rows():
        out = base()
        made, _ = P9.scene_rows(random.Random(6577))
        failed = [r for r in MC.failed_rows(random.Random(6779)) if r["case"] == "failed"]
        for x in random.Random(6578).sample(made, 40) + random.Random(6780).sample(failed, 20):
            lines = x["text"].split("\n")
            scene = next(t[len("scene: "):] for t in lines if t.startswith("scene: "))
            out.append({"before": [t[len("before: "):] for t in lines if t.startswith("before: ")], "bot": None,
                        "scene": scene, "scene_parts": scene_parts_v67(scene), "line": lines[-1][len("now: "):]})
        return out
    E.test_rows = rows
    E.main()


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts["v67"], ensure_ascii=False, indent=1), counts["v66_rows"], "+", counts["v67_rows"], "=", len(rows), "rows")
        rng = random.Random(3)
        for r in rng.sample(rows[-counts["v67_rows"]:], 30):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        train(seed)
    elif what == "gguf":
        gguf(seed)
    elif what == "export":
        export(seed)
    else:
        print(__doc__)
