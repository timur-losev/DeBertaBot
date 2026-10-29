"""How well the brain reads the lines of round v66: the v65 brain (the baseline) against v66 (plan: chains2/ml_v66/PLAN_v66.md).

    python measure_v66.py answers <decoder>        the decoder's English for every Russian and Spanish line (and the English
                                                   lines of hand_v66), with the scene and the lines before: <decoder> = v65
                                                   (models/coop-qwen3-qlora-chains9-v65) or v66 -> measure_v66_answers_<decoder>.json
    python measure_v66.py score <bot> <decoder>    every English line read by the bot's ensemble and its place matcher
                                                   -> measure_v66_<bot>_<decoder>.log

Sets:
  owner66   owner_lines_v66.json (the owner's English lines of 2026-10-25 22:04 .. 2026-10-27 01:20; bot v66 is trained on them,
            bot v65 is not)
  hand66    chains2/ml_v66/hand_v66.json (trained on: a check that they are learnt)
  test66    chains2/ml_v66/test_v66.json (200 lines written blind, held out: never trained on): the order and the place
A line is right when the intent read is the label's; it is right in place too when the label's place is none, or the line's
primary target names it (the object or the zone), or, with a line before, it points at it ("it", "that": the planner's memory
of the line before). As the game reads them: a Russian or Spanish line through the decoder with its lines before and scene;
an English line by the classifier as it is, except where the scene may change it (coop_cli Hear, as measure_v65.py).
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
ML66 = os.path.join(HERE, "chains2", "ml_v66")
ADAPTERS = {"v65": os.path.join(MODELS, "coop-qwen3-qlora-chains9-v65", "pieces10v65_final_seed0"),
            "v66": os.path.join(MODELS, "coop-qwen3-qlora-chains10-v66", "pieces11v66_final_seed0")}
NO_PLACE = {"GIVE_WAY", "WHAT_IS_IT", "GO_BACK", "HELP_INTERACTION", "SWITCH_WEAPON", "RELOAD", "SEE_ME", "SMALL_TALK", "PRAISE",
            "KILL_YOURSELF", "HOLSTER", "STATUS_REPORT", "BODY_STATE", "DROP"}


def jl(*p):
    return json.load(io.open(os.path.join(*p), encoding="utf-8"))


def n(t):
    return re.sub(r"[\s.!?¿¡,]+", " ", t.strip().lower()).strip()


def sets():
    """{set: [{"id", "lang", "before", "scene", "text", "label", "place"?, "en"?}]}. A test item equal to a hand row (the
    owner's own line, trained on) is left out (sets.left_out)."""
    sets.left_out = []
    out = {"owner66": [], "hand66": [], "test66": []}
    for o in jl(COOP, "owner_lines_v66.json")["items"]:
        out["owner66"].append({"id": o["id"], "lang": "en", "before": [], "scene": None, "text": o["text"], "label": o["maj"]})
    for k, it in enumerate(jl(ML66, "hand_v66.json")["items"]):
        out["hand66"].append({"id": f"hand66_{k:03d}", "lang": it["lang"], "before": it["before"], "scene": it.get("scene") or None,
                              "text": it["text"], "en": it["en"], "label": it["label"]})
    seen = {(tuple(n(b) for b in h["before"]), (h.get("scene") or "").strip().lower(), n(h["text"])) for h in out["hand66"]}
    p = os.path.join(ML66, "test_v66.json")
    if os.path.exists(p):
        for it in jl(p)["items"]:
            if (tuple(n(b) for b in it.get("before", [])), (it.get("scene") or "").strip().lower(), n(it["text"])) in seen:
                sets.left_out.append(it["id"])     # the owner said it: a hand row the decoder is trained on
                continue
            out["test66"].append({"id": it["id"], "lang": it["lang"], "before": it.get("before", []), "scene": it.get("scene") or None,
                                  "text": it["text"], "label": it["label"], "place": it.get("place"), "rule": it.get("rule")})
    return out


def turn_text(it, scene=True):
    lines = [f"before: {b}" for b in it["before"]]
    if scene and it.get("scene"):
        lines.append(f"scene: {it['scene']}")
    return "\n".join(lines + [f"now: {re.sub(r'[.!?]+$', '', it['text'].strip()).lower() if it['lang'] != 'en' else it['text']}"])


def answers(decoder):
    sys.path.insert(0, HERE)
    import chains8_v64 as P8      # the chain modules: Qwen3 + the LoRA, the system turn, generation
    from peft import PeftModel
    P, C, C2, Q = P8.P, P8.C, P8.C2, P8.Q
    system = __import__("chains9_v65").SYSTEM_V65 if decoder == "v65" else __import__("chains10_v66").SYSTEM_V66
    model, tok = Q.load(C.NAME)
    model = PeftModel.from_pretrained(model, ADAPTERS[decoder])
    turns = Q.Turns(tok, system)
    gen(model, turns, os.path.join(HERE, f"measure_v66_answers_{decoder}.json"), decoder, C, C2)


def gen(model, turns, path, decoder, C, C2):
    out = {}
    for name, items in sets().items():
        todo = [it for it in items if it["lang"] != "en" or name != "owner66"]
        if todo:
            out[name] = dict(zip([it["id"] for it in todo], C.generate(model, turns, [turn_text(it) for it in todo], max_new=C2.MAX_NEW["pieces"])))
    json.dump({"decoder": decoder, "pred": out}, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("answers ->", path, flush=True)


def score(bot, decoder):
    os.environ["COOP_TAG"] = bot
    sys.path.insert(0, COOP)
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import coop_v2 as V
    import locations as L
    folder = os.path.join(MODELS, f"coop-deberta-v3-ens3-{bot}")
    cfg = jl(folder, "bot_config.json")
    pred = jl(HERE, f"measure_v66_answers_{decoder}.json")["pred"]
    norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()   # noqa: E731
    split = lambda a: [p.strip() for p in a.split("\n") if p.strip()] or [""]   # noqa: E731
    data = sets()
    texts = set()
    for name, items in data.items():
        for it in items:
            if it["lang"] == "en":
                texts.add(norm(it["text"]))
            if name != "owner66":
                texts.add(norm(split(pred.get(name, {}).get(it["id"], ""))[0]))
            if "en" in it:
                texts.add(norm(it["en"][0]))
    texts = sorted(texts)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    runs = []
    for m in cfg["members"]:
        tk = AutoTokenizer.from_pretrained(os.path.join(folder, m))
        model = AutoModelForSequenceClassification.from_pretrained(os.path.join(folder, m), dtype=torch.float32).to(dev).eval()
        rows = []
        with torch.no_grad():
            for i in range(0, len(texts), 128):
                x = tk(texts[i:i + 128], padding=True, truncation=True, max_length=64, return_tensors="pt").to(dev)
                rows += torch.softmax(model(**x).logits, -1).cpu().tolist()
        runs.append(rows)
        del model
    pick, top = {}, {}
    for n, t in enumerate(texts):
        p = [sum(r[n][j] for r in runs) / len(runs) for j in range(len(V.INTENTS))]
        pick[t] = V.pick(p, cfg["gate"], cfg["threshold"])[0]
        top[t] = V.INTENTS[max(range(len(p)), key=p.__getitem__)]

    def scene_look(it):
        sc = it.get("scene") or ""
        t = top[norm(it["text"])]
        return bool(sc) and (("standing on a " in sc and t in ("TAKE_COVER", "MOVE_TO", "NONE", "GET_OUT", "CROUCH", "FOLLOW_ME"))
                             or ("a car " not in sc and t == "GET_IN"))

    def place_ok(it, text, got):
        want = it.get("place")
        if not want or got in NO_PLACE:
            return True
        r = L.record(text)
        t = r["targets"][r["primary"]] if r["primary"] >= 0 else None
        if t is None:
            return False
        if t["object"] == want or t["zone"] == want:
            return True
        return bool(it["before"]) and t["pointer"] in ("it", "this") and t["object"] is None
    log = io.StringIO()
    print(f"bot {bot}, decoder {decoder}; test66 items left out as the owner's own trained lines: {sets.left_out}", file=log)
    for name, items in data.items():
        if not items:
            continue
        right, placed, rows, by, rules = 0, 0, [], {}, {}
        for it in items:
            if it["lang"] == "en" and not scene_look(it):
                read_text = it["text"]
            else:
                read_text = split(pred.get(name, {}).get(it["id"], ""))[0]
            got = pick[norm(read_text)]
            want = it["label"]
            ok = got == want
            okp = ok and place_ok(it, read_text, got)
            right += ok
            placed += okp
            rows.append((ok, okp, it, read_text, got, want))
            b = by.setdefault(it["lang"], [0, 0])
            b[0] += okp
            b[1] += 1
            if it.get("rule") is not None:
                r = rules.setdefault(it["rule"], [0, 0])
                r[0] += okp
                r[1] += 1
        langs = ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items()))
        print(f"\n{name}: intent {right}/{len(items)} = {100 * right / len(items):.1f}%, intent and place {placed}/{len(items)} = "
              f"{100 * placed / len(items):.1f}%   ({langs})", file=log)
        if rules:
            print("  by rule: " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in sorted(rules.items())), file=log)
        for ok, okp, it, read_text, got, want in rows:
            if not okp:
                why = "" if ok else f"read {got:14s} want {want}"
                if ok:
                    why = f"place: want {it.get('place')}"
                print(f"  NO  {it['text'][:44]:44s} {('-> ' + read_text[:44]) if read_text != it['text'] else '':47s} {why}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v66_{bot}_{decoder}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    if sys.argv[1] == "answers":
        answers(sys.argv[2])
    else:
        score(sys.argv[2], sys.argv[3])
