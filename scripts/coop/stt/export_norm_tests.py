"""Test data for the C++ twin of `norm` (coop::SpeechTextForClassifier in cpp/coop_intent): every Parakeet transcript
of the study and a few edge cases, each with what build_v4.py / build_v51.py give the classifier for it.

    python export_norm_tests.py        # writes norm_tests.json
    ..\\..\\..\\cpp\\coop_intent\\build\\Release\\coop_cli.exe --speech-text-tests norm_tests.json

The C++ function lowercases ASCII letters only (Parakeet prints ASCII: every transcript here is); a capital letter
outside ASCII would stay as it is, where Python lowercases it. No such line is in this file.
"""
import glob, io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()      # as in build_v4.py, build_v5.py, build_v51.py
EDGE = ["", " ", "Go.", "Go!?", "go .", " Go. ", "GO NOW!!!", "Wait... what?", "Don't shoot.", "\tHold fire!\t", "a.b.c.", "...",
        "?", "Okay, so. Breach!", "café.", "two, on the left", "Look at me...  ", " Fall back. ", "No. 3", "hold\n"]
texts = list(EDGE)
for f in sorted(glob.glob(os.path.join(HERE, "out_parakeet-0.6b-v2_*.json"))):
    texts += [r["text"] for r in json.load(io.open(f, encoding="utf-8"))["rows"]]
texts = list(dict.fromkeys(texts))
assert all(not any(c.isupper() and ord(c) > 127 for c in t) for t in texts)
json.dump([{"text": t, "norm": norm(t)} for t in texts], io.open(os.path.join(HERE, "norm_tests.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print(len(texts), "distinct lines;", sum(norm(t) != t for t in texts), "of them change")
