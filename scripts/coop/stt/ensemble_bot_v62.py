"""bot_config.json for the v62 ensemble (the v6x line: the bot that talks and carries, make_spec_v62.py), with the gate and the
threshold fitted on build_v62.py's own out-of-fold runs (three seeds, five folds each, the recipe that is shipped), then export_cpp.py,
gen_tests.py and gen_world_tests.py for its cpp/ directory (--no-tests: the config and the ONNX files only). Prints the
numbers: the fitted gate and threshold, VCTK pool B (speakers that only read test lines), typed, the v60 lines alone, and
the older lines alone (what the shooter's lines lost or won).

    python ensemble_bot_v62.py [--no-tests]

The v62 lines (blind/v62) are reported alone, the v60 and older lines beside them.
"""
import io, json, os, subprocess, sys
os.environ["COOP_TAG"] = "v62"
HERE = os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, COOP)
import coop_v2 as V

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-deberta-v3-ens3-v62"))
assert all(os.path.exists(os.path.join(OUT, f"seed{s}", "model.safetensors")) for s in (0, 1, 2)), "no final v62 members"
items = {i["id"]: i for i in V.load_items() if i["maj"]}
seeds = {s["id"]: s for s in V.seed_items()}
spoken = lambda i: i["author"] in ("r6", "cs")  # noqa: E731
runs = [json.load(io.open(os.path.join(HERE, f"finaloof62_{s}.json"), encoding="utf-8"))["probs"] for s in (0, 1, 2)]
probs = {}
for r in runs:
    for k, v in r.items():
        probs.setdefault(k, []).append(v)
probs = {k: [sum(x[j] for x in v) / len(v) for j in range(len(V.INTENTS))] for k, v in probs.items() if len(v) == 3}


def by(c, keep=lambda i: True):
    return {k.split("|", 1)[1]: v for k, v in probs.items()
            if k.split("|", 1)[0] == c and k.split("|", 1)[1] in items and keep(items[k.split("|", 1)[1]])}


def crit(p, gate, t):
    s = V.score(V.picks(p, gate, t), [items[k] for k in p])
    return s, 100 * (s["near"] - 2 * s["cross"])


best = None
for gate in ("top", "family"):
    for t in range(0, 100, 2):
        near = cross = 0
        for c in ("clean", "kokoro", "kokorox", "vctkA"):
            s = V.score(V.picks(by(c, spoken), gate, t / 100), [items[k] for k in by(c, spoken)])
            near += s["near_count"]; cross += s["cross_count"]
        v = near - 2 * cross
        # a tie between the gates goes to the family gate (v58's rule: the family gate reads the chains better)
        if best is None or v > best[0] or (v == best[0] and gate == "family" and best[1] != "family"):
            best = (v, gate, t / 100)
_, gate, thr = best
print(f"v62 ensemble, build_v62.py out-of-fold (three seeds): gate {gate}, threshold {thr:.2f}")
for name, p in (("VCTK pool B, r6+cs", by("vctkB", spoken)), ("typed, all lines", by("typed")),
                ("typed, v62 lines", by("typed", lambda i: i["version"] == "v62")),
                ("VCTK pool B, v62 lines", by("vctkB", lambda i: spoken(i) and i["version"] == "v62")),
                ("typed, v60 lines", by("typed", lambda i: i["version"] == "v60")),
                ("VCTK pool B, v60 lines", by("vctkB", lambda i: spoken(i) and i["version"] == "v60")),
                ("typed, v1-v58 lines", by("typed", lambda i: i["version"] not in ("v60", "v62"))),
                ("VCTK pool B, v1-v58", by("vctkB", lambda i: spoken(i) and i["version"] not in ("v60", "v62")))):
    s, c = crit(p, gate, thr)
    print(f"  {name:24} n={s['n']:4}  near {100 * s['near']:.1f}  wrong family {100 * s['cross']:.1f}%  criterion {c:.1f}")
for name, cond in (("Russian voices, r6+cs", "ru"), ("German voices, r6+cs", "de")):
    s, c = crit(by(cond, spoken), gate, thr)
    print(f"  {name:24} n={s['n']:4}  near {100 * s['near']:.1f}  wrong family {100 * s['cross']:.1f}%  criterion {c:.1f}")
# the owner's own heard lines, out of fold: right, wrong family (acted wrongly), say again; per line as heard and per time said
owner = json.load(io.open(os.path.join(COOP, "owner_lines_v61.json"), encoding="utf-8"))["items"]
_rel = json.load(io.open(os.path.join(COOP, "annot", "v62", "relabel_v62.json"), encoding="utf-8"))["owner"]
owner = [dict(o, maj=_rel[o["id"]]["to"]) if o["id"] in _rel else o for o in owner]   # three praise lines (build_v62.py)
op = {k.split("|", 1)[1]: v for k, v in probs.items() if k.startswith("owner|")}
assert len(op) == len(owner), (len(op), len(owner))
for name, weight in (("owner, per line", lambda o: 1), ("owner, per time said", lambda o: o["count"])):
    n = right = wrong = again = 0
    for o in owner:
        p = V.pick(op[o["id"]], gate, thr)[0]
        w = weight(o)
        n += w
        right += w * (p == o["maj"])
        if p != o["maj"]:
            if p == "NONE" and o["maj"] != "NONE":
                again += w
            elif V.FAMILY[p] != V.FAMILY[o["maj"]]:
                wrong += w
    print(f"  {name:24} n={n:4}  right {100 * right / n:.1f}  say again / ignored {100 * again / n:.1f}%  "
          f"wrong family {100 * wrong / n:.1f}%")
cfg = {"labels": V.INTENTS, "threshold": thr, "gate": gate, "families": V.FAMILY,
       "phrases": {k: v["label"] for k, v in V.I.items()}, "base_model": "microsoft/deberta-v3-base", "members": ["seed0", "seed1", "seed2"],
       "recipe": {"max_len": 64, "batch": 16, "epochs": 12, "weight_decay": 0.01, "warmup": 0.1, "lr": 5e-05, "dtype": "float32", "seeds": [0, 1, 2]},
       "trained_on": f"{len(items)} lines from 3 AI-written authors + {len(seeds)} seed commands (seed_commands_v62.json), typed, plus what "
                     f"{len(owner)} of the owner's own heard lines (owner_lines_v61.json, labelled from the talk), plus what "
                     "Parakeet TDT 0.6B v2 heard when the r6 and cs lines and the seed commands were read by synthesized voices (Windows, Kokoro, "
                     "VCTK pool A, and the Russian and German Windows voices reading English); transcripts that are word for word a typed command "
                     "of another intent left out, accented ones that keep too little of their line too (build_v62.py)",
       "threshold_from": "build_v62.py's 5-fold out-of-fold predictions, three seeds with their own splits, averaged, on the r6 and cs lines "
                         "as Parakeet heard them from the training voices; criterion near - 2*wrong-family. Work-machine build (CUDA)",
       "input": "speech-to-text output lowercased, final .!? stripped, inner punctuation kept"}
json.dump(cfg, io.open(os.path.join(OUT, "bot_config.json"), "w", encoding="utf-8"), indent=1)
env = {**os.environ, "HF_HUB_OFFLINE": "1", "COOP_TAG": "v62"}
subprocess.run([sys.executable, os.path.join(COOP, "export_cpp.py"), OUT], check=True, env=env)
if "--no-tests" in sys.argv:
    sys.exit(0)
subprocess.run([sys.executable, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_tests.py"), OUT], check=True, env=env)
subprocess.run([sys.executable, os.path.join(COOP, "..", "..", "cpp", "coop_intent", "tools", "gen_world_tests.py"), OUT], check=True, env=env)
