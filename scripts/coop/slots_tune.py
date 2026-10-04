"""
Chooses, per model, the form of the two slot questions -- on dev_slots.json only.

The first dev run asked timing as a two-way choice with descriptions and got "on my signal" for
almost everything (laya:en kept 'now' on 11 of 49 lines, gliclass on 0). Candidate forms:

  timing   choice+desc   {"right now": ..., "on my signal": ...}          (the first run)
           choice        {"right now": null, "on my signal": null}
           noul          "The player says to wait for their signal before doing it."
  reference choice+desc  this one / the other one / no object, with descriptions
           choice        the same, bare
           noul          "The order is about the other one of two things."

    python slots_tune.py        # writes slots_chosen.json
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_coop as C  # noqa: E402

D = json.load(io.open(os.path.join(HERE, "dev_slots.json"), encoding="utf-8"))
MODELS = ["laya:en", "von:1.1", "gliclass:large", "decision:eos", "nli:latest"]

TIMING_FORMS, REF_FORMS = C.TIMING_FORMS, C.REF_FORMS


def read(model, form_name, form, text, kind):
    ans, ms = C.ollaya(model, text, {"s": form})
    lab, probs = ans["s"]
    if form["type"] == "noul":
        pos = lab >= 0.5  # a noul answer is the probability that the statement holds
        return ("on_signal" if pos else "now") if kind == "timing" else ("other" if pos else "not_other")
    if kind == "timing":
        return C.TIMING[lab]
    return C.REF[lab] if C.REF[lab] == "other" else "not_other"


def main():
    chosen = {}
    for kind, forms, rows in (("timing", TIMING_FORMS, D["timing"]), ("reference", REF_FORMS, D["reference"])):
        print(f"\n{kind}: {len(rows)} dev lines")
        for m in MODELS:
            best = None
            line = f"  {m:<16}"
            for fname, form in forms.items():
                hit = 0
                for text, want in rows:
                    got = read(m, fname, form, text, kind)
                    w = want if kind == "timing" else ("other" if want == "other" else "not_other")
                    hit += got == w
                line += f"  {fname} {hit:>2}/{len(rows)}"
                if best is None or hit > best[0]:
                    best = (hit, fname)
            chosen.setdefault(m, {})[kind] = best[1]
            print(line + f"   -> {best[1]}")
    C.save(True)
    json.dump(chosen, io.open(os.path.join(HERE, "slots_chosen.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
