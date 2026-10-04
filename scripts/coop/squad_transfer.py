"""
Does the fine-tuned laya still work with a menu it was not fine-tuned on? A per-line look, after a
review found the first answer (42/46 vs 38/46, one number) could not carry that claim.

The squad bot's menu (../commands.json, 16 options with descriptions) overlaps the co-op one: five
labels are identical ('follow me', 'hold position', 'cover me', 'fall back', 'revive me'), and six of
the 46 scored lines of ../testset.json are verbatim seed commands the model was trained on. So the
lines are split:
  seed copies     the 6 lines that are also seed commands (trained on; not evidence of transfer)
  new intents     lines whose answer is an intent the co-op menu does not have (ATTACK_TARGET,
                  CEASE_FIRE, TAKE_COVER, HEAL_ME, LOOT_AREA, STATUS_REPORT, SWITCH_WEAPON, STEALTH_MODE)
  overlapping     the rest (intents with a co-op counterpart, and NONE)
Also a parity check of the PyTorch copy against ollaya on this menu, which is the one that triggers
layout.rs's per-option truncation (16 options with descriptions exceed the 176-token room).

    python squad_transfer.py            # needs the ollaya daemon for the parity part
"""
import io, json, os, re, sys, urllib.request

import torch
from safetensors.torch import load_file

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import laya_torch as L  # noqa: E402
import seed_check  # noqa: E402

SQUAD = os.path.normpath(os.path.join(HERE, ".."))
FT = os.path.normpath(os.path.join(HERE, "..", "..", "models", "coop-laya-ft"))
NEW = {"ATTACK_TARGET", "CEASE_FIRE", "TAKE_COVER", "HEAL_ME", "LOOT_AREA", "STATUS_REPORT",
       "SWITCH_WEAPON", "STEALTH_MODE"}
INSTR = "Which order is the player giving the squad bot?"
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def main():
    cmds = {k: v for k, v in json.load(io.open(os.path.join(SQUAD, "commands.json"), encoding="utf-8")).items()
            if not k.startswith("_")}
    crit = {v["label"]: v["description"] for v in cmds.values()}
    back = {v["label"]: k for k, v in cmds.items()}
    cases = [c for c in json.load(io.open(os.path.join(SQUAD, "testset.json"), encoding="utf-8"))["cases"]
             if c.get("want") is not None]
    seeds = {norm(s["text"]) for s in seed_check.seed_items()}
    E = L.Encoder()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    zs, _, _ = L.load_laya()
    ft = L.Laya(FT)
    ft.load_state_dict(load_file(os.path.join(FT, "model.safetensors")))
    zs.to(dev).eval()
    ft.to(dev).eval()

    rows = []
    for c in cases:
        want = c["want"] if isinstance(c["want"], list) else [c["want"]]
        ids, mk, labels = E.build(f'Player said: "{c["text"]}"', INSTR, crit)
        with torch.no_grad():
            b = [t.to(dev) for t in E.batch([(ids, mk, 0)])]
            pz = torch.softmax(zs(*b)[0, :len(labels)] / E.temperature("choice", len(labels)), -1).tolist()
            pf = torch.softmax(ft(*b)[0, :len(labels)], -1).tolist()
        az = back[labels[max(range(len(pz)), key=pz.__getitem__)]]
        af = back[labels[max(range(len(pf)), key=pf.__getitem__)]]
        group = ("seed copy" if norm(c["text"]) in seeds else
                 "new intent" if any(w in NEW for w in want) else "overlapping")
        rows.append({"text": c["text"], "want": want, "group": group, "zero": az, "ft": af,
                     "pz": dict(zip(labels, pz))})

    print(f"{'group':<12} {'n':>3} {'zero-shot':>10} {'fine-tuned':>11}   changed lines")
    for g in ("seed copy", "new intent", "overlapping"):
        rs = [r for r in rows if r["group"] == g]
        z = sum(r["zero"] in r["want"] for r in rs)
        f = sum(r["ft"] in r["want"] for r in rs)
        ch = [f"{r['text']!r}: {r['zero']} -> {r['ft']} ({'ok' if r['ft'] in r['want'] else 'wrong'})"
              for r in rs if (r["zero"] in r["want"]) != (r["ft"] in r["want"])]
        print(f"{g:<12} {len(rs):>3} {z:>10} {f:>11}")
        for line in ch:
            print(f"      {line}")
    tz = sum(r["zero"] in r["want"] for r in rows)
    tf = sum(r["ft"] in r["want"] for r in rows)
    print(f"{'all':<12} {len(rows):>3} {tz:>10} {tf:>11}")

    # parity on this menu (the truncation path): PyTorch zero-shot vs ollaya, per line
    gaps, agree = [], 0
    for r in rows:
        body = {"model": "laya:en", "state": f'Player said: "{r["text"]}"', "keep_alive": "5m",
                "questions": {"q": {"type": "choice", "instructions": INSTR, "criteria": crit}}}
        a = json.loads(urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:11435/api/decide", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}), timeout=300).read())["answers"]["q"]
        agree += back[a["choice"]] == r["zero"]
        gaps.append(max(abs(a["probabilities"][k] - v) for k, v in r["pz"].items()))
    print(f"\nparity on the squad menu (truncation path): same argmax on {agree}/{len(rows)} lines, "
          f"max probability gap {max(gaps):.4f}")
    json.dump(rows, io.open(os.path.join(HERE, "results_squad_transfer.json"), "w", encoding="utf-8"),
              indent=1, default=list)


if __name__ == "__main__":
    main()
