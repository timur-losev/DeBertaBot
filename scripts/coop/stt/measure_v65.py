"""How well the brain reads the owner's lines of 2026-10-25 and the lines written down for round v65: the v64 brain (the
baseline) against v65. The owner, 2026-10-25: "запускай и померяем точность".

    python measure_v65.py answers <decoder>   (the chain modules' environment) the decoder's English for every Russian and
                                               Spanish line (and the English lines of hand_v65), with the scene when the set
                                               has one: <decoder> = v64 (models/coop-qwen3-qlora-chains8-v64) or v65
                                               -> measure_v65_answers_<decoder>.json
    python measure_v65.py score <bot> <decoder>  (COOP_TAG=v64 or v65) every English line read by the bot's ensemble:
                                               the owner's English lines as they are (the game sends them to the classifier:
                                               router 0.00 in the logs), the others as the decoder wrote them
                                               -> measure_v65_<bot>_<decoder>.log

Sets:
  owner65   owner_lines_v65.json (33 English lines, labelled from the talk; the label is the first order of the line)
  hand65    chains2/ml_v65/hand_v65.json (70 rows; the label: the intent the owner meant, by hand)
  scene65   chains2/ml_v65/scene_test.json when it exists (held out: never trained on): a line with a scene, the order the
            scene calls for
A line is right when the intent read is the label's (COLLECT and DELIVER apart: keeping and bringing are not the same).
As the game reads them: a Russian or Spanish line through the decoder (v64: without the scene, which it was never shown; v65:
with it); an English line by the classifier as it is, except, with v65, a line the scene may change (coop_cli Hear: the bot
stands on a thing and the classifier reads TAKE_COVER, MOVE_TO, NONE, GET_OUT, CROUCH or FOLLOW_ME; no car near and it
reads GET_IN), which goes through the decoder with the scene.
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
ML65 = os.path.join(HERE, "chains2", "ml_v65")
ADAPTERS = {"v64": os.path.join(MODELS, "coop-qwen3-qlora-chains8-v64", "pieces9v64_final_seed0"),
            "v65": os.path.join(MODELS, "coop-qwen3-qlora-chains9-v65", "pieces10v65_final_seed0")}


def jl(*p):
    return json.load(io.open(os.path.join(*p), encoding="utf-8"))


def sets():
    """{set: [{"id", "lang", "before", "scene", "text", "label" (intent) or "en" (English answers, labelled by the bot)}]}"""
    out = {"owner65": [], "hand65": [], "scene65": []}
    for o in jl(COOP, "owner_lines_v65.json")["items"]:
        out["owner65"].append({"id": o["id"], "lang": "en", "before": [], "scene": None, "text": o["text"], "label": o["maj"]})
    for k, it in enumerate(jl(ML65, "hand_v65.json")["items"]):
        out["hand65"].append({"id": f"hand65_{k:03d}", "lang": it["lang"], "before": it["before"], "scene": it.get("scene"),
                              "text": it["text"], "en": it["en"], "label": it["label"]})
    p = os.path.join(ML65, "scene_test.json")
    if os.path.exists(p):
        for it in jl(p)["items"]:
            out["scene65"].append({"id": it["id"], "lang": it["lang"], "before": it.get("before", []), "scene": it["scene"],
                                   "text": it["text"], "label": it["label"]})
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
    system = P.SYSTEM_V62 if decoder == "v64" else __import__("chains9_v65").SYSTEM_V65
    model, tok = Q.load(C.NAME)
    model = PeftModel.from_pretrained(model, ADAPTERS[decoder])
    turns = Q.Turns(tok, system)
    out = {}
    for name, items in sets().items():
        todo = [it for it in items if it["lang"] != "en" or name != "owner65"]
        if not todo:
            continue
        got = C.generate(model, turns, [turn_text(it, decoder != "v64") for it in todo], max_new=C2.MAX_NEW["pieces"])
        out[name] = dict(zip([it["id"] for it in todo], got))
    path = os.path.join(HERE, f"measure_v65_answers_{decoder}.json")
    json.dump({"decoder": decoder, "adapter": ADAPTERS[decoder], "pred": out}, io.open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("answers ->", path)


def score(bot, decoder):
    os.environ["COOP_TAG"] = bot
    sys.path.insert(0, COOP)
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import coop_v2 as V
    folder = os.path.join(MODELS, f"coop-deberta-v3-ens3-{bot}")
    cfg = jl(folder, "bot_config.json")
    pred = jl(HERE, f"measure_v65_answers_{decoder}.json")["pred"]
    norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()   # noqa: E731
    split = lambda a: [p.strip() for p in a.split("\n") if p.strip()] or [""]   # noqa: E731
    data = sets()
    texts = set()
    for name, items in data.items():
        for it in items:
            if it["lang"] == "en":
                texts.add(norm(it["text"]))
            if name != "owner65":
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
        """coop_cli Hear: an English line of one order goes to the decoder with the scene when the scene may change it."""
        sc = it.get("scene") or ""
        t = top[norm(it["text"])]
        return decoder != "v64" and bool(sc) and (("standing on a " in sc and t in ("TAKE_COVER", "MOVE_TO", "NONE", "GET_OUT", "CROUCH", "FOLLOW_ME"))
                                                  or ("a car " not in sc and t == "GET_IN"))
    log = io.StringIO()
    print(f"bot {bot}, decoder {decoder}", file=log)
    for name, items in data.items():
        if not items:
            continue
        right, rows, looked = 0, [], 0
        for it in items:
            if it["lang"] == "en" and not scene_look(it):
                read_text = it["text"]
            else:
                read_text = split(pred.get(name, {}).get(it["id"], ""))[0]
                looked += it["lang"] == "en"
            got = pick[norm(read_text)]
            want = it["label"] if "label" in it else pick[norm(it["en"][0])]
            ok = got == want
            right += ok
            rows.append((ok, it, read_text, got, want))
        by = {}
        for ok, it, *_ in rows:
            b = by.setdefault(it["lang"], [0, 0])
            b[0] += ok
            b[1] += 1
        langs = ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items()))
        print(f"\n{name}: {right}/{len(items)} = {100 * right / len(items):.1f}%   ({langs}; English lines the scene sent to the decoder: {looked})", file=log)
        for ok, it, read_text, got, want in rows:
            if not ok:
                print(f"  NO  {it['text'][:44]:44s} {('-> ' + read_text) if read_text != it['text'] else '':40s} read {got:14s} want {want}", file=log)
    print(log.getvalue(), end="")
    io.open(os.path.join(HERE, f"measure_v65_{bot}_{decoder}.log"), "w", encoding="utf-8").write(log.getvalue())


if __name__ == "__main__":
    if sys.argv[1] == "answers":
        answers(sys.argv[2])
    else:
        score(sys.argv[2], sys.argv[3])
