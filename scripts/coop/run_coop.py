"""
Co-op bot voice orders -> one intent enum (+ timing and reference slots), every model we have.

Truth for the test set is three readings per line: the blind author's intent and two blind
annotators' intents (blind/author_*.json, annot/author_*_ann*.json).
  maj      the intent at least two of the three chose       -> top-1
  accept   intents at least two of the three accept         -> "correct"
  any      intents at least one accepts                      -> outside it: nobody defends the pick
Errors are split by what the bot then does:
  safe     it did nothing harmful: NONE, WAIT or HOLD_POSITION
  wrong    it did a different action than asked
  LOUD     that different action is loud or committing (breach, frag, flash, smoke, entry, go now,
           window, rappel, plant, defuse) -- the ones that lose a round

    python run_coop.py                 # dev: choosing thresholds and combinations
    python run_coop.py --test          # the held-out numbers
"""
import glob, hashlib, io, json, os, statistics, sys, time, urllib.request, urllib.error
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAYA = os.environ.get("OLLAYA_URL", "http://127.0.0.1:11435") + "/api/decide"
QWEN = os.environ.get("QWEN_URL", "http://127.0.0.1:8000") + "/api/run-parallel"
CACHE_PATH = os.path.join(HERE, "cache_coop.json")

I = {k: v for k, v in json.load(io.open(os.path.join(HERE, "intents.json"), encoding="utf-8")).items()
     if not k.startswith("_")}
INTENTS = list(I)
SAFE = {"NONE", "WAIT", "HOLD_POSITION"}
LOUD = {"BREACH", "FRAG", "FLASH", "SMOKE", "ENTRY", "GO_NOW", "VAULT_WINDOW", "RAPPEL", "PLANT", "DEFUSE"}
INSTR = "Which order is the player giving the bot?"

# Families: a mix-up inside one is a near miss the game's owner accepts ("the bot may be a little
# dumb and literal": BREACH for ENTRY is fine). Across families, or acting on a non-order, is not.
FAMILY = {"BREACH": "assault", "ENTRY": "assault", "VAULT_WINDOW": "assault", "RAPPEL": "assault",
          "FLASH": "utility", "SMOKE": "utility", "FRAG": "utility",
          "HOLD_POSITION": "hold", "HOLD_ANGLE": "hold", "HOLD_OTHER_ANGLE": "hold", "COVER_ME": "hold",
          "FOLLOW_ME": "move", "MOVE_TO": "move", "FLANK": "move",
          "PLANT": "objective", "DEFUSE": "objective", "DRONE": "scout", "REVIVE_ME": "revive",
          "FALL_BACK": "retreat", "WAIT": "stop", "GO_NOW": "go", "NONE": "none"}

TIMING = {"right now": "now", "on my signal": "on_signal"}
TIMING_DESC = {"right now": "do it immediately", "on my signal": "wait for my go, on my call, on three"}
REF = {"this one": "this", "the other one": "other", "no object": "none"}
REF_DESC = {"this one": "this, that, here, a specific thing", "the other one": "the other door, window or angle",
            "no object": "no particular object named"}

# Slot question forms; which one each model gets is chosen on dev_slots.json by slots_tune.py.
TIMING_FORMS = {
    "choice+desc": {"type": "choice", "instructions": "When should the bot do it?", "criteria": TIMING_DESC},
    "choice": {"type": "choice", "instructions": "When should the bot do it?",
               "criteria": {k: None for k in TIMING}},
    "noul": {"type": "noul", "instructions": "The player says to wait for their signal before doing it."},
}
REF_FORMS = {
    "choice+desc": {"type": "choice", "instructions": "Which object is the order about?", "criteria": REF_DESC},
    "choice": {"type": "choice", "instructions": "Which object is the order about?",
               "criteria": {k: None for k in REF}},
    "noul": {"type": "noul", "instructions": "The order is about the other one of two things, not this one."},
}


def _slot(ans, kind):
    v, probs = ans
    if probs is None:  # noul
        return ("on_signal" if v >= 0.5 else "now") if kind == "timing" else ("other" if v >= 0.5 else "this")
    return TIMING[v] if kind == "timing" else REF[v]


try:
    CHOSEN = json.load(io.open(os.path.join(HERE, "slots_chosen.json")))
except Exception:
    CHOSEN = {}

try:
    CACHE = json.load(io.open(CACHE_PATH, encoding="utf-8"))
except Exception:
    CACHE = {}
_dirty = [0]


def save(force=False):
    if _dirty[0] and (force or _dirty[0] >= 200):
        json.dump(CACHE, io.open(CACHE_PATH, "w", encoding="utf-8"))
        _dirty[0] = 0


def _post(url, body, timeout=900):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    return r, (time.perf_counter() - t0) * 1000


def wording(style):
    """-> ({shown label: description or None}, {shown label: INTENT})"""
    if style == "code":
        return {k: None for k in INTENTS}, {k: k for k in INTENTS}
    if style == "phrase":
        return {I[k]["label"]: None for k in INTENTS}, {I[k]["label"]: k for k in INTENTS}
    if style == "phrase+desc":
        return {I[k]["label"]: I[k]["description"] for k in INTENTS}, {I[k]["label"]: k for k in INTENTS}
    raise ValueError(style)


def ollaya(model, text, questions):
    key = hashlib.sha1(json.dumps([model, questions, text], sort_keys=True).encode()).hexdigest()
    if key not in CACHE:
        r, ms = _post(OLLAYA, {"model": model, "state": f'Player said: "{text}"',
                               "questions": questions, "keep_alive": "60m"})
        CACHE[key] = [{q: ([a["noul"], None] if a["type"] == "noul" else [a["choice"], a["probabilities"]])
                      for q, a in r["answers"].items()}, ms]
        _dirty[0] += 1
        save()
    return CACHE[key]


def classify(model, style, text, slots=False):
    """-> intent, pmax, ms, timing|None, reference|None"""
    crit, back = wording(style)
    qs = {"intent": {"type": "choice", "instructions": INSTR, "criteria": crit}}
    if slots:
        ch = CHOSEN.get(model, {"timing": "choice+desc", "reference": "choice+desc"})
        qs["timing"] = TIMING_FORMS[ch["timing"]]
        qs["reference"] = REF_FORMS[ch["reference"]]
    ans, ms = ollaya(model, text, qs)
    lab, probs = ans["intent"]
    t = _slot(ans["timing"], "timing") if slots else None
    r = _slot(ans["reference"], "reference") if slots else None
    return back[lab], max(probs.values()), ms, t, r


def classify_qwen(text, menu, slots=False):
    labels = {I[k]["label"]: k for k in INTENTS}
    schema = {"intent": {"type": "enum", "choices": list(labels),
                         "description": "Which order the player is giving the bot"}}
    if slots:
        schema["timing"] = {"type": "enum", "choices": list(TIMING), "description": "When the bot should do it"}
        schema["reference"] = {"type": "enum", "choices": list(REF), "description": "Which object the order is about"}
    ctx = f'A player in a tactical shooter said to their AI teammate: "{text}"'
    if menu:
        ctx += "\nOrders the bot understands:\n" + "\n".join(
            f"- {I[k]['label']}: {I[k]['description']}" for k in INTENTS)
    key = hashlib.sha1(json.dumps(["qwen", schema, ctx], sort_keys=True).encode()).hexdigest()
    if key not in CACHE:
        r, ms = _post(QWEN, {"context": ctx, "schema": schema})
        ft = r["field_telemetry"]
        CACHE[key] = [{f: [ft[f]["value"], {c["choice"]: c["probability"] for c in ft[f]["top_choices"]}]
                       for f in schema}, ms]
        _dirty[0] += 1
        save()
    ans, ms = CACHE[key]
    lab, probs = ans["intent"]
    t = TIMING[ans["timing"][0]] if slots else None
    r = REF[ans["reference"][0]] if slots else None
    return labels[lab], max(probs.values()), ms, t, r


# ---------------------------------------------------------------- data

def load_test():
    items = []
    for path in sorted(glob.glob(os.path.join(HERE, "blind", "author_*.json"))):
        if path.endswith("_lines.json"):
            continue
        key = os.path.basename(path)[len("author_"):-len(".json")]
        auth = json.load(io.open(path, encoding="utf-8"))
        anns = [json.load(io.open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(HERE, "annot", f"author_{key}_ann*.json")))]
        assert len(anns) == 2, (key, len(anns))
        for a in auth:
            reads = [{"intent": a["intent"], "set": {a["intent"]}, "timing": a.get("timing", "now"),
                      "reference": a.get("reference", "none")}]
            for an in anns:
                x = an[a["id"]]
                reads.append({"intent": x["intent"], "set": {x["intent"]} | set(x.get("ok", [])),
                              "timing": x.get("timing", "now"), "reference": x.get("reference", "none")})
            votes = Counter(r["intent"] for r in reads)
            top, n = votes.most_common(1)[0]
            acc = Counter(i for r in reads for i in r["set"])
            tv = Counter(r["timing"] for r in reads).most_common(1)[0]
            rv = Counter(r["reference"] for r in reads).most_common(1)[0]
            items.append({"id": a["id"], "author": key, "text": a["text"], "kind": a.get("kind", "plain"),
                          "maj": top if n >= 2 else None, "unanimous": n == 3,
                          "accept": {i for i, c in acc.items() if c >= 2}, "any": set(acc),
                          "timing": tv[0] if tv[1] >= 2 else None,
                          "reference": rv[0] if rv[1] >= 2 else None,
                          "author_intent": a["intent"], "reads": reads})
    return items


def load_dev():
    d = json.load(io.open(os.path.join(HERE, "dev.json"), encoding="utf-8"))["cases"]
    out = []
    for i, c in enumerate(d):
        want = c["intent"] if isinstance(c["intent"], list) else [c["intent"]]
        out.append({"id": f"dev_{i:03d}", "author": "dev", "text": c["text"],
                    "kind": ("negated" if len(want) > 1 and "WAIT" in want else
                             "on_signal" if c.get("timing") == "on_signal" else
                             "other_ref" if c.get("reference") == "other" else
                             "none" if want == ["NONE"] else "plain"),
                    "maj": want[0], "unanimous": True, "accept": set(want), "any": set(want),
                    "timing": c.get("timing", "now"), "reference": c.get("reference")})
    return out


# ---------------------------------------------------------------- scoring

def score(preds, items):
    """preds: {id: intent}. Returns counts as fractions of the items."""
    n = len(items)
    top = sum(1 for it in items if it["maj"] and preds[it["id"]] == it["maj"])
    n_maj = sum(1 for it in items if it["maj"])
    ok = sum(1 for it in items if preds[it["id"]] in it["accept"])
    safe = wrong = loud = 0
    for it in items:
        p = preds[it["id"]]
        if p in it["accept"]:
            continue
        if p in SAFE:
            safe += 1
        else:
            wrong += 1
            loud += p in LOUD
    near = cross = fired = n_none = 0
    for it in items:
        p = preds[it["id"]]
        good = p in it["accept"] or (it["maj"] and FAMILY[p] == FAMILY[it["maj"]])
        near += bool(good)
        if not good and p not in SAFE:
            cross += 1
        if it["maj"] == "NONE":
            n_none += 1
            fired += p not in SAFE
    return {"n": n, "top1": top / max(n_maj, 1), "ok": ok / n, "safe": safe / n,
            "wrong": wrong / n, "loud": loud / n, "near": near / n, "cross": cross / n,
            "fired_on_nonorder": fired / max(n_none, 1)}


def gate(raw, thr):
    """raw: {id: (intent, pmax)} -> {id: intent}, below-threshold picks become NONE."""
    return {k: (v[0] if v[1] >= thr else "NONE") for k, v in raw.items()}


# ---------------------------------------------------------------- combinations and slots

TOP = ["laya:en phrase", "von:1.1 phrase", "gliclass:large phrase", "nli:latest phrase",
       "decision:eos phrase+desc", "qwen phrase"]


def two_key(raw, items, thr, test):
    """The bot acts only when two models, each past its own dev threshold, name the same intent;
    otherwise it does nothing (NONE). Pairs chosen on dev; all pairs printed."""
    print("\nTWO-KEY: act only if both models agree (each at its dev threshold), else do nothing")
    out = {}
    for i, a in enumerate(TOP):
        for b in TOP[i + 1:]:
            ga, gb = gate(raw[a], thr[a]), gate(raw[b], thr[b])
            p = {k: (ga[k] if ga[k] == gb[k] else "NONE") for k in ga}
            s = score(p, items)
            out[f"{a} & {b}"] = s
    for k, s in sorted(out.items(), key=lambda x: -x[1]["ok"])[:8]:
        print(f"  {k:<52} ok {100*s['ok']:>3.0f}  safe {100*s['safe']:>3.0f}  wrong {100*s['wrong']:>3.0f}"
              f"  LOUD {100*s['loud']:>3.0f}")
    return out


def slot_study(items):
    """Timing and reference as their own questions, in the same request as the intent.
    Also the design question for 'hold the other angle': a flat enum value, or HOLD_ANGLE + reference."""
    print("\nSLOTS: timing (now / on my signal) and reference (this / other / none), same request")
    runs = {m: (lambda t, m=m, s=s: classify(m, s, t, slots=True)) for m, s in
            (("laya:en", "phrase"), ("von:1.1", "phrase"), ("gliclass:large", "phrase"),
             ("decision:eos", "phrase+desc"), ("nli:latest", "phrase"))}
    runs["qwen"] = lambda t: classify_qwen(t, False, slots=True)
    out = {}
    sig = [it for it in items if it["timing"] == "on_signal"]
    now = [it for it in items if it["timing"] == "now" and it["maj"] not in (None, "NONE")]
    other = [it for it in items if it["reference"] == "other"]
    notother = [it for it in items if it["reference"] in ("this", "none") and it["maj"] not in (None, "NONE")]
    angle_other = [it for it in items if it["maj"] == "HOLD_OTHER_ANGLE"]
    angle_this = [it for it in items if it["maj"] == "HOLD_ANGLE"]
    print(f"  lines: on_signal {len(sig)}, now {len(now)}, other {len(other)}, not other {len(notother)},"
          f" HOLD_OTHER_ANGLE {len(angle_other)}, HOLD_ANGLE {len(angle_this)}")
    print(f"  {'model':<16} {'signal kept':>11} {'now kept':>9} {'fires early':>11} {'other found':>11}"
          f" {'false other':>11} {'flat other-angle':>16} {'slot other-angle':>16}")
    for m, fn in runs.items():
        res = {it["id"]: fn(it["text"]) for it in items}
        save()
        kept = sum(1 for it in sig if res[it["id"]][3] == "on_signal")
        nowk = sum(1 for it in now if res[it["id"]][3] == "now")
        # the round-losing error on an on-signal order: the bot acts now (timing now, or GO_NOW)
        early = sum(1 for it in sig if res[it["id"]][3] == "now" or res[it["id"]][0] == "GO_NOW")
        of = sum(1 for it in other if res[it["id"]][4] == "other")
        fo = sum(1 for it in notother if res[it["id"]][4] == "other")
        flat = sum(1 for it in angle_other if res[it["id"]][0] == "HOLD_OTHER_ANGLE")
        flat_this = sum(1 for it in angle_this if res[it["id"]][0] == "HOLD_ANGLE")

        def slot_angle(r):
            if r[0] not in ("HOLD_ANGLE", "HOLD_OTHER_ANGLE"):
                return r[0]
            return "HOLD_OTHER_ANGLE" if r[4] == "other" else "HOLD_ANGLE"
        slot = sum(1 for it in angle_other if slot_angle(res[it["id"]]) == "HOLD_OTHER_ANGLE")
        slot_this = sum(1 for it in angle_this if slot_angle(res[it["id"]]) == "HOLD_ANGLE")
        out[m] = {"signal_kept": kept / max(len(sig), 1), "now_kept": nowk / max(len(now), 1),
                  "fires_early": early / max(len(sig), 1), "other_found": of / max(len(other), 1),
                  "false_other": fo / max(len(notother), 1),
                  "flat_other_angle": [flat, len(angle_other), flat_this, len(angle_this)],
                  "slot_other_angle": [slot, len(angle_other), slot_this, len(angle_this)]}
        print(f"  {m:<16} {kept:>5}/{len(sig):<5} {nowk:>4}/{len(now):<4} {early:>5}/{len(sig):<5}"
              f" {of:>5}/{len(other):<5} {fo:>5}/{len(notother):<5}"
              f" {flat:>4}/{len(angle_other)} +{flat_this:>2}/{len(angle_this):<5}"
              f" {slot:>4}/{len(angle_other)} +{slot_this:>2}/{len(angle_this)}")
    save(True)
    return out


# ---------------------------------------------------------------- main

CONFIGS = [(m, s) for m in ("laya:en", "laya:multilingual", "von:1.1", "gliclass:large", "nli:latest")
           for s in ("code", "phrase", "phrase+desc")] + [("decision:eos", "phrase"), ("decision:eos", "phrase+desc")]


def run_all(items):
    raw, lat = {}, {}
    for m, s in CONFIGS:
        name = f"{m} {s}"
        raw[name], ms = {}, []
        for it in items:
            p, pm, t, _, _ = classify(m, s, it["text"])
            raw[name][it["id"]] = (p, pm)
            ms.append(t)
        lat[name] = statistics.median(ms)
        save()
    for menu in (False, True):
        name = "qwen phrase" + (" + menu in context" if menu else "")
        raw[name], ms = {}, []
        for it in items:
            p, pm, t, _, _ = classify_qwen(it["text"], menu)
            raw[name][it["id"]] = (p, pm)
            ms.append(t)
        lat[name] = statistics.median(ms)
    save(True)
    return raw, lat


def main():
    test = "--test" in sys.argv
    items = load_test() if test else load_dev()
    print(f"{'test' if test else 'dev'}: {len(items)} lines")
    if test:
        print(f"  majority on {sum(1 for i in items if i['maj'])}, unanimous on "
              f"{sum(1 for i in items if i['unanimous'])}, author outvoted by both annotators on "
              f"{sum(1 for i in items if i['maj'] and i['maj'] != i['author_intent'])}")
        # ceiling: each reader against the other two
        hits = n = 0
        for it in items:
            for j in range(3):
                others = [it["reads"][k] for k in range(3) if k != j]
                if others[0]["intent"] == others[1]["intent"]:
                    n += 1
                    hits += it["reads"][j]["intent"] == others[0]["intent"]
        print(f"  one reader vs the other two (ceiling): {100*hits/n:.0f}% top-1")
    raw, lat = run_all(items)

    # thresholds: chosen on dev, applied to test
    thr_path = os.path.join(HERE, "thresholds_dev.json")
    if not test:
        thr = {}
        for name, r in raw.items():
            best = max(((score(gate(r, t / 100), items)["ok"] - 2 * score(gate(r, t / 100), items)["wrong"], -t)
                        for t in range(0, 100, 2)))
            thr[name] = -best[1] / 100
        json.dump(thr, io.open(thr_path, "w"), indent=1)
    thr = json.load(io.open(thr_path))

    kinds = sorted({it["kind"] for it in items})
    print(f"\n{'config':<34} {'thr':>4} {'top1':>5} {'ok':>4} {'safe':>5} {'wrong':>6} {'LOUD':>5} {'ms':>6}"
          f"   ok by kind: " + " ".join(f"{k[:9]:>9}" for k in kinds))
    table = {}
    for name, r in raw.items():
        for t in (0.0, thr[name]):
            if t == thr[name] and t == 0.0 and name in table:
                continue
            p = gate(r, t)
            s = score(p, items)
            byk = {k: score(p, [i for i in items if i["kind"] == k])["ok"] for k in kinds}
            table[f"{name} @{t:.2f}"] = {**s, "by_kind": byk, "ms": lat[name]}
            print(f"{name:<34} {t:>4.2f} {100*s['top1']:>5.0f} {100*s['ok']:>4.0f} {100*s['safe']:>5.0f} "
                  f"{100*s['wrong']:>6.0f} {100*s['loud']:>5.0f} {lat[name]:>6.0f}   "
                  + " ".join(f"{100*byk[k]:>9.0f}" for k in kinds))
    ens = two_key(raw, items, thr, test)
    slots = slot_study(items)
    json.dump({"table": table, "thresholds": thr, "two_key": ens, "slots": slots,
               "raw": {k: v for k, v in raw.items()}},
              io.open(os.path.join(HERE, f"results_coop_{'test' if test else 'dev'}.json"), "w",
                      encoding="utf-8"), indent=1, default=list)


if __name__ == "__main__":
    main()
