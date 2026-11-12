"""Round v70 of the chains study (2026-11-11): decoder v70, for the owner's body commands (2026-11-08) and driving by voice
(2026-11-11): «Едь вперед поверни налево», «Едь к банку»; plan chains2/ml_v70/TODO_v70.md, the canon in its section 10.

What changes against v69s5 (chains13_v69.py with V69_RUN=5, the deployed decoder):
  - v69s5's rows as they are (its own fixes and drops included);
  - round v70's rows (chains2/ml_v70/make_rows_v70.py): driving in the car (the game's scene "a car 0 m away") -> "drive forward",
    "turn left at the next junction", "take the second right", "turn the car around", "drive to the bank", "park the car", "drive
    faster" / "drive slower", "stop the car", two orders in a line; «едь к X» in any scene; the same words on foot as v69s5 writes
    them; the body's commands -> the game's body command lines ("raise arm_r 90 left 20 speed 2", "hook left hard"); a strike at
    someone stays "kick him"; combos -> "teach двойка = jab ; punch", "play двойка", "forget двойка", "combos". The body's and the
    combos' rows get a neutral scene a third of the time, as v68's and v69's;
  - rows equal to a held-out item are dropped: the tests v69s5 kept out, and round v70's blind test
    (chains2/ml_v70/test_v70_new.json: a row is dropped when its line is one of its lines, whatever before);
  - v69s5's recipe: the short system turn, a new LoRA on plain Qwen3-1.7B, r16, 3 epochs.

    python chains14_v70.py data       the rows, counted, with samples
    python chains14_v70.py train      -> models/coop-qwen3-qlora-chains14-v70/pieces14v70_final_seed0; answers on the test sets
    python chains14_v70.py gguf | export      -> models/coop-chain-v70/cpp
"""
import io, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["V69_RUN"] = "5"
import chains13_v69 as P13               # v69s5's machinery and rows
from chains13_v69 import P12, P10, C2, P
ML70 = os.path.join(C2.CH2, "ml_v70")
sys.path.insert(0, ML70)
import make_rows_v70 as R70

TAG = "v70"
VARIANT = f"pieces14{TAG}_final"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = P.ROWS_OF
P12.TAG, P12.VARIANT = TAG, VARIANT
P12.ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains14-v70")
TEST70 = os.path.join(ML70, "test_v70_new.json")
_training_v69 = P13.training


def test70_lines():
    """The lines no new row may have: round v70's blind test's."""
    if not os.path.exists(TEST70):
        raise SystemExit(f"{TEST70} is missing: the blind test is written before the rows are trained")
    items = json.load(io.open(TEST70, encoding="utf-8"))["items"]
    return {P10.norm(it["text"]) for it in items}, len(items)


def training():
    rows, counts, split = _training_v69()
    new = R70.decoder_rows(random.Random(7001))
    drive = [r for r in new if r["case"].startswith(("drive", "foot"))]           # their scenes are their own
    body = P12.with_neutral_scenes([r for r in new if not r["case"].startswith(("drive", "foot"))], random.Random(7002))
    held, _ = P12.test_keys()
    t70, n70 = test70_lines()
    owner, _ = P13.owner_lines()
    gen = drive + body
    kept = [r for r in gen if P10.row_key(r["text"]) not in held and P10.norm(r["text"].split("now: ")[-1]) not in t70 | owner]
    # the blind test's lines are kept out of the old rows too
    old_n = len(rows)
    rows = [r for r in rows if P10.norm(r["text"].split("now: ")[-1]) not in t70]
    by = {}
    for r in kept:
        by[f"{r['case']}/{r['lang']}"] = by.get(f"{r['case']}/{r['lang']}", 0) + 1
    counts["v70"] = {"generated": by, "test70_items": n70, "dropped_as_test": len(gen) - len(kept),
                     "old_rows_dropped_as_test70": old_n - len(rows)}
    counts["v69s5_rows"], counts["v70_rows"] = len(rows), len(kept)
    return rows + [{"text": r["text"], "answer": r["answer"]} for r in kept], counts, split


P12.training = training


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts["v70"], ensure_ascii=False, indent=1))
        print(counts["v69s5_rows"], "+", counts["v70_rows"], "=", len(rows), "rows")
        rng = random.Random(3)
        for r in rng.sample(rows[-counts["v70_rows"]:], 20):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        P12.train(seed)
    elif what == "gguf":
        P12.gguf(seed)
    elif what == "export":
        P12.export(seed)
    else:
        print(__doc__)
