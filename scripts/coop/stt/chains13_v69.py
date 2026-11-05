"""Round v69 of the chains study (2026-11-04): decoder v69. The owner: «начинай обучение» (the misreads of his voice tests of
2026-10-31 .. 11-04, chains2/ml_v68/TODO_v68.md section 5, logged and held since 2026-11-02).

What changes against v68s2 (chains12_v68.py with V68_RUN=2, the deployed decoder):
  - v68s2's rows (79,271), with the bare «вернись» / «возвращайся» / «vuelve» rows written "go back", not "come back"
    (make_rows_v69.fix_old_rows; the owner, 2026-11-03: «вернись» is the previous place);
  - round v69's rows (chains2/ml_v69/make_rows_v69.py: doors in, out and shut, lying, sitting and getting off a thing, carrying
    to a thing in the dative, the orders of a line that were lost, "up onto", going back, staying here, a wall said after, a queued
    pair, "try again", remarks that are no order, "using A and B, bring the box to C"), a third of them with a neutral scene as
    v68's;
  - rows equal to an item of a held-out test are dropped: v67's, v68's timer test, and the owner test of round v69
    (chains2/ml_v69/test_v69_owner.json: his own misread lines; a row is dropped when its line is one of them, whatever before);
  - v68s2's recipe: the short system turn, a new LoRA on plain Qwen3-1.7B, r16, 3 epochs, alone on the GPU.

V69_RUN: "" for the first run (v69, trained 2026-11-04 01:55-04:51: the owner test 17 -> 42 of 47, but test67 lost 8 items at
"+ means", where a thing is the step: run 1's get_off and put_climb rows), "2" for v69s2 (make_rows_v69 run 2: no put_climb, which
said the opposite of the rounds before, and the contrast rows means_from), "3" for v69s3 (v69s2, deployed 2026-11-04 08:18, was
taken back at 09:0x: the memory scenarios failed 27 steps, because statements that teach were written as orders («Это верстак.» ->
"climb onto the crate"), «когда я скажу давай, …» lost "on my go", «вернись обратно» after «сядь» was "sit back down"; run 3 adds
make_rows_v69's statement, on_go_davai, back_after, here_bare, remark_fail, use_climb, forget_thing and short_after, and keeps
the memory scenarios' lines out of the new rows), "4" for v69s4 (v69s3 was better on the owner's lines, but 5 memory steps
and about 20 of his 495 real lines were harmed: «Используя коробку залезть …» -> "come back to me", «иди ко мне сюда» -> "come here |
stay here", «Давай.» after an order on the go -> the order again, «No.» -> "sit down"; run 4 adds make_rows_v69's KINDS_4; stopped at 13:58 for the owner's answers), "5" for v69s5 (run 4's rows with the owner's answers of
2026-11-04 ~14:00: «поставь X и залезь на Y» puts X down first, «используя его» makes it the step -- put_then rows, means_from's
Spanish «pon X y súbete» likewise, 344 old rows that read a plain putting as the means left out; bare «стой» is "wait").

    python chains13_v69.py data       the rows, counted, with samples
    python chains13_v69.py train      -> models/coop-qwen3-qlora-chains13-v69/pieces13v69_final_seed0; answers on the test sets
    python chains13_v69.py gguf | export      -> models/coop-chain-v69/cpp       (V69_RUN=2: v69s2 in all three names)
"""
import io, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["V68_RUN"] = "2"
import chains12_v68 as P12               # v68s2's machinery and rows
from chains12_v68 import P10, C2, P
ML69 = os.path.join(C2.CH2, "ml_v69")
sys.path.insert(0, ML69)
import make_rows_v69 as R69

RUN = int(os.environ.get("V69_RUN") or 1)
TAG = "v69" if RUN == 1 else f"v69s{RUN}"
VARIANT = f"pieces13{TAG}_final"
C2.KIND[VARIANT] = "pieces"
C2.FINAL[VARIANT] = P.ROWS_OF
P12.TAG, P12.VARIANT = TAG, VARIANT
P12.ADAPTER = os.path.join(P.MODELS, "coop-qwen3-qlora-chains13-v69")
OWNER_TEST = os.path.join(ML69, "test_v69_owner.json")
_training_v68 = P12.training


MEMORY_SCENARIOS = os.path.normpath(os.path.join(HERE, "..", "memory_scenarios.json"))


def owner_lines():
    """The lines no row may have: the owner test's."""
    items = json.load(io.open(OWNER_TEST, encoding="utf-8"))["items"]
    return {P10.norm(it["text"]) for it in items}, len(items)


def scenario_lines():
    """Run 3 on: the memory scenarios' lines (scripts/coop/memory_scenarios.json, the teaching the decoder must leave alone: v69s2
    failed 27 of their steps), which no new row may have. The old rows keep theirs («Да.», «Давай.»: v68s2 learnt them and passes)."""
    if RUN < 3:
        return set()
    d = json.load(io.open(MEMORY_SCENARIOS, encoding="utf-8"))
    return {P10.norm(st["say"]) for sc in (d["scenarios"] if isinstance(d, dict) else d) for st in sc.get("steps", []) if isinstance(st.get("say"), str)}


def training():
    rows, counts, split = _training_v68()
    rows, back_fixed = R69.fix_old_rows(rows)
    put_dropped = 0
    if RUN >= 5:     # the owner, 2026-11-04: «поставь X и залезь» puts X down first (make_rows_v69.drop_put_using)
        rows, put_dropped = R69.drop_put_using(rows)
    new = P12.with_neutral_scenes(R69.decoder_rows(random.Random(6901), RUN), random.Random(6902))
    held, _ = P12.test_keys()
    owner, n_owner = owner_lines()
    scen = scenario_lines()
    kept = [r for r in new if P10.row_key(r["text"]) not in held and P10.norm(r["text"].split("now: ")[-1]) not in owner | scen]
    # the owner's lines are kept out of the old rows too
    old_n = len(rows)
    rows = [r for r in rows if P10.norm(r["text"].split("now: ")[-1]) not in owner]
    by = {}
    for r in kept:
        by[f"{r['case']}/{r['lang']}"] = by.get(f"{r['case']}/{r['lang']}", 0) + 1
    counts["v69"] = {"generated": by, "old_rows_back_fixed": back_fixed, "owner_test_items": n_owner,
                     "dropped_as_test": len(new) - len(kept), "old_rows_dropped_as_owner_test": old_n - len(rows),
                     "old_put_using_rows_dropped": put_dropped}
    counts["v68s2_rows"], counts["v69_rows"] = len(rows), len(kept)
    return rows + [{"text": r["text"], "answer": r["answer"]} for r in kept], counts, split


P12.training = training


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if what == "data":
        rows, counts, split = training()
        print(json.dumps(counts["v69"], ensure_ascii=False, indent=1))
        print(counts["v68s2_rows"], "+", counts["v69_rows"], "=", len(rows), "rows")
        rng = random.Random(3)
        for r in rng.sample(rows[-counts["v69_rows"]:], 25):
            print("----\n" + r["text"] + "\n=> " + r["answer"].replace("\n", " | "))
    elif what == "train":
        P12.train(seed)
    elif what == "gguf":
        P12.gguf(seed)
    elif what == "export":
        P12.export(seed)
    else:
        print(__doc__)
