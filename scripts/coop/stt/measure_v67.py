"""How well the brain reads the lines of round v67 (any thing with any order; plan: chains2/ml_v67/PLAN_v67.md).

    python measure_v67.py answers <decoder>     the decoder's English for every line of test67 (all three languages), with
                                                its lines before and scene: <decoder> = v66, v67 or v67s (the short system
                                                turn) -> measure_v67_answers_<decoder>.json

Sets:
  test67    chains2/ml_v67/test_v67.json (240 lines written blind, held out: never trained on): the orders each line must give,
            each with its intent, target and means (an object and a qualifier).
The whole brain's score (classifier, matcher, planner) is measure_v67_cli.py's.
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
ML67 = os.path.join(HERE, "chains2", "ml_v67")
ADAPTERS = {"v66": os.path.join(MODELS, "coop-qwen3-qlora-chains10-v66", "pieces11v66_final_seed0"),
            "v67": os.path.join(MODELS, "coop-qwen3-qlora-chains11-v67", "pieces12v67_final_seed0"),
            "v67s": os.path.join(MODELS, "coop-qwen3-qlora-chains11-v67", "pieces12v67s_final_seed0")}


def jl(*p):
    return json.load(io.open(os.path.join(*p), encoding="utf-8"))


def sets():
    """{"test67": [{"id", "lang", "before", "scene", "text", "want"}]}"""
    out = {"test67": []}
    for it in jl(ML67, "test_v67.json")["items"]:
        out["test67"].append({"id": it["id"], "lang": it["lang"], "before": it.get("before") or [], "scene": it.get("scene") or None,
                              "text": it["line"], "want": it["want"], "cat": it.get("cat")})
    return out


def turn_text(it, scene=True):
    lines = [f"before: {b}" for b in it["before"]]
    if scene and it.get("scene"):
        lines.append(f"scene: {it['scene']}")
    return "\n".join(lines + [f"now: {re.sub(r'[.!?]+$', '', it['text'].strip()).lower() if it['lang'] != 'en' else it['text']}"])


def gen(model, turns, path, decoder, C, C2):
    out = {}
    for name, items in sets().items():
        out[name] = dict(zip([it["id"] for it in items], C.generate(model, turns, [turn_text(it) for it in items], max_new=C2.MAX_NEW["pieces"])))
    json.dump({"decoder": decoder, "pred": out}, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("answers ->", path, flush=True)


def answers(decoder):
    sys.path.insert(0, HERE)
    import chains8_v64 as P8
    from peft import PeftModel
    C, C2, Q = P8.C, P8.C2, P8.Q
    system = (__import__("chains10_v66").SYSTEM_V66 if decoder == "v66" else
              __import__("chains11_v67").SYSTEM_V67S if decoder == "v67s" else __import__("chains11_v67").SYSTEM_V67)
    model, tok = Q.load(C.NAME)
    model = PeftModel.from_pretrained(model, ADAPTERS[decoder])
    turns = Q.Turns(tok, system)
    gen(model, turns, os.path.join(HERE, f"measure_v67_answers_{decoder}.json"), decoder, C, C2)


if __name__ == "__main__":
    if sys.argv[1:2] == ["answers"]:
        answers(sys.argv[2])
    else:
        print(__doc__)
