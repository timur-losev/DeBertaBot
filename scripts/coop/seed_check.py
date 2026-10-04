"""
Does adding the developer's seed commands (seed_commands.json) to training hurt the blind test?

Leave-one-author-out as everywhere: train on two authors (+ all seed lines), score the third author's
lines only. Compared with the same recipe without seeds (train_bert.py results, same seeds 0-2).
Also shows how the canonical probes the live test failed on are classified with and without seeds.

    python seed_check.py            # jev environment, GPU if available
"""
import io, json, os, sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_coop as C  # noqa: E402
import train_bert as T  # noqa: E402

NAME = "microsoft/deberta-v3-base"
PROBES = ["come here", "go there", "breach", "follow me", "hold", "go", "smoke", "one left",
          "get over here", "blow that wall", "move to the ping", "stick with me",
          # negated lines kept OUT of the seeds: the user's own from the live test, and new ones
          "do not come to me", "don't reach me", "do not revieve", "please don't follow me",
          "don't blow that wall", "dont breach", "don't go through the window", "never flank"]


def seed_items():
    d = json.load(io.open(os.path.join(HERE, "seed_commands.json"), encoding="utf-8"))
    out = []
    for intent, lines in d.items():
        if intent.startswith("_"):
            continue
        for n, t in enumerate(lines):
            out.append({"id": f"seed_{intent}_{n}", "text": t, "maj": intent, "accept": {intent},
                        "any": {intent}, "author": "seed", "kind": "seed"})
    return out


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    items = C.load_test()
    seeds = seed_items()
    probes = [{"id": f"probe_{i}", "text": t} for i, t in enumerate(PROBES)]
    path = os.path.join(HERE, "results_seed_check.json")
    try:
        res = json.load(io.open(path, encoding="utf-8"))
    except Exception:
        res = {}
    for held in T.AUTHORS:
        train = [i for i in items if i["author"] != held] + seeds
        test = [i for i in items if i["author"] == held]
        for s in T.SEEDS:
            k = f"{held}/{s}"
            if k in res:
                continue
            probs, _, _ = T.train_predict(NAME, train, test + probes, s, device)
            res[k] = probs
            json.dump(res, io.open(path, "w", encoding="utf-8"))
            print(f"held={held} seed={s} done", flush=True)


if __name__ == "__main__":
    main()
