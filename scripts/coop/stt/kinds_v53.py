"""Bot v53's out-of-fold picks on the v53 lines of r6 and cs, by the kind the author wrote the line for: the exact intent,
not only the family (HOLD_ANGLE and HOLD_OTHER_ANGLE share one). Gate and threshold from bot_config.json.

    python kinds_v53.py > score_v53_kinds.log
"""
import io, json, os, sys
from collections import Counter
os.environ["COOP_TAG"] = "v53"
COOP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, COOP)
import coop_v2 as V

cfg = json.load(io.open(os.path.join(COOP, "..", "..", "models", "coop-deberta-v3-ens3-v53", "bot_config.json"), encoding="utf-8"))
gate, thr = cfg["gate"], cfg["threshold"]
items = {i["id"]: i for i in V.load_items() if i["maj"]}
runs = [json.load(io.open(os.path.join(COOP, "stt", f"finaloof53_{s}.json"), encoding="utf-8")) for s in (0, 1, 2)]
probs = {k: [sum(r["probs"][k][j] for r in runs) / 3 for j in range(len(V.INTENTS))] for k in runs[0]["probs"]}
SHOW = [("typed", "typed"), ("clean", "Windows"), ("kokoro", "Kokoro EN"), ("kokorox", "Kokoro other"), ("vctkA", "VCTK seen"), ("vctkB", "VCTK unseen")]
new = [i for i in items.values() if i["version"] == "v53" and i["author"] in ("r6", "cs")]
print(f"gate {gate}, threshold {thr}; {len(new)} v53 lines of r6 and cs; exact = the bot acts on the line's own intent (or does nothing on a NONE line)")
groups = [("jump (JUMP)", lambda i: i["kind"] == "jump"), ("boundary (window, rope, move, cover, breach)", lambda i: i["kind"] == "boundary"),
          ("angle: the bot takes the other (HOLD_OTHER_ANGLE)", lambda i: i["kind"] == "angle" and i["maj"] == "HOLD_OTHER_ANGLE"),
          ("angle: the player takes the other (HOLD_ANGLE)", lambda i: i["kind"] == "angle" and i["maj"] == "HOLD_ANGLE"),
          ("fire: cease fire in radio wording (HOLD_FIRE)", lambda i: i["kind"] == "fire" and i["maj"] == "HOLD_FIRE"),
          ("fire: reports of being under fire (NONE)", lambda i: i["kind"] == "fire" and i["maj"] == "NONE"),
          ("negated jumps (NONE)", lambda i: i["kind"] == "negated")]
for title, keep in groups:
    ids = [i["id"] for i in new if keep(i)]
    row = []
    for c, label in SHOW:
        p = {k: probs[f"{c}|{k}"] for k in ids if f"{c}|{k}" in probs}
        pk = V.picks(p, gate, thr)
        ok = sum(pk[k] == items[k]["maj"] for k in p)
        wrong = Counter(pk[k] for k in p if pk[k] != items[k]["maj"])
        row.append(f"{label} {ok}/{len(p)}" + (" (" + ", ".join(f"{a} {b}" for a, b in wrong.most_common(3)) + ")" if wrong else ""))
    print(f"  {title}: " + " | ".join(row))
print("  (a pick shown as NONE on an order line is the bot doing nothing: it asked again or took the line for chatter)")
