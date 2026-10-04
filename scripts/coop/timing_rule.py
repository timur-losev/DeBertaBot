"""
Timing and "the other one" as code rules instead of model questions. Both patterns were written from
dev_slots.json only. The test lines existed by then, and the models' aggregate slot scores on them had
been seen, but no on-signal or other-ref test line had been read. Treat the counts as upper bounds:
blind/spec.json itself names "on their call / when they say go / on three", which primes the authors
toward exactly the phrases the timing pattern keys on, and 15 test lines repeat dev lines verbatim.

    python timing_rule.py
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_coop as C  # noqa: E402

ON_SIGNAL = re.compile(
    r"\b(on|at) (my|the) (go|call|mark|signal|count|word|command)\b"
    r"|\bwhen i (say|call|give|tell|shout)"
    r"|\bon (one|two|three|1|2|3)\b"
    r"|\b(wait|hold) (for|till|until) (my|i)\b"
    r"|\b(till|until) i say", re.I)
OTHER = re.compile(r"\b(other|another|opposite)\b", re.I)


def main():
    items = [i for i in C.load_test() if i["timing"]]
    dev = json.load(io.open(os.path.join(HERE, "dev_slots.json"), encoding="utf-8"))["timing"]
    d_ok = sum((bool(ON_SIGNAL.search(t)) == (w == "on_signal")) for t, w in dev)
    sig = [i for i in items if i["timing"] == "on_signal"]
    now = [i for i in items if i["timing"] == "now" and i["maj"] not in (None, "NONE")]
    kept = sum(1 for i in sig if ON_SIGNAL.search(i["text"]))
    nowk = sum(1 for i in now if not ON_SIGNAL.search(i["text"]))
    print(f"dev_slots: {d_ok}/{len(dev)}")
    print(f"test: signal kept {kept}/{len(sig)}, now kept {nowk}/{len(now)}")
    print("missed on-signal lines:")
    for i in sig:
        if not ON_SIGNAL.search(i["text"]):
            print("   ", repr(i["text"]))
    oth = [i for i in items if i["reference"] == "other"]
    noth = [i for i in C.load_test() if i["reference"] in ("this", "none") and i["maj"] not in (None, "NONE")]
    found = sum(1 for i in oth if OTHER.search(i["text"]))
    false = sum(1 for i in noth if OTHER.search(i["text"]))
    print(f"test: 'the other one' found {found}/{len(oth)}, false 'other' {false}/{len(noth)}")
    json.dump({"signal_kept": [kept, len(sig)], "now_kept": [nowk, len(now)],
               "other_found": [found, len(oth)], "false_other": [false, len(noth)]},
              io.open(os.path.join(HERE, "results_timing_rule.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
