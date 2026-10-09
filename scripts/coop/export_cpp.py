"""
Everything the C++ engine (../../cpp/coop_intent) needs from the fine-tuned DeBERTa bot, plus the
golden data it is checked against. Writes into <bot dir>/cpp/:

  model.onnx          the classifier, input_ids + attention_mask -> one logit per intent, dynamic batch
                      and sequence length, opset 17 (ONNX Runtime >= 1.13, what UE5's NNE embeds);
                      an ensemble writes model0.onnx, model1.onnx, ... instead
  vocab.tsv           the Unigram vocabulary: one "piece<TAB>score" per line, line number = token id
  intent_config.json  labels, families, phrases, threshold, gate, member files, special ids and added
                      tokens, max length, the three regexes, the map's named places ("locations")
  golden.jsonl        per line: text, the token ids the Python tokenizer produces, PyTorch probabilities
                      (the members' average for an ensemble)

The tokenizer the model was trained with is transformers' fast DebertaV2 tokenizer, which is NOT the
sentencepiece pipeline: normalizer = collapse whitespace runs / \\n\\r\\t to one space, NFC, strip right;
pre-tokenizer = Metaspace (prepend U+2581 always, split into words); model = Unigram. The C++ port
reproduces that pipeline, so the golden ids come from the same tokenizer object the bot uses.

    python export_cpp.py [BOT_DIR]      # jev environment; default: the shipped bot (bots.py)
    python export_cpp.py [BOT_DIR] --config-only    # after editing locations.json or the regexes: no ONNX export
"""
import io, json, os, re, sys

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# the bot to export: argv[1], a directory with bot_config.json (train_final.py / train_v2.py final);
# an ensemble lists its member directories in bot_config "members" and becomes model0.onnx, model1.onnx...
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
CONFIG_ONLY = "--config-only" in sys.argv     # rewrite intent_config.json and vocab.tsv, keep the ONNX files and golden.jsonl
import bots  # noqa: E402
MODEL = os.path.normpath(_ARGS[0] if _ARGS else bots.default_bot())
OUT = os.path.join(MODEL, "cpp")
# the golden lines are the lines and seeds of the study the bot was trained in: its bot_config names
# the seed file, and the seed file names the COOP_TAG (the v1 bot names none: the default study)
_SEEDS = re.search(r"seed_commands_(v[0-9]+)", json.load(io.open(os.path.join(MODEL, "bot_config.json"),
                                                                 encoding="utf-8")).get("trained_on", ""))
if _SEEDS:
    if os.environ.get("COOP_TAG", _SEEDS.group(1)) != _SEEDS.group(1):
        sys.exit(f"COOP_TAG={os.environ['COOP_TAG']} but {MODEL} was trained under {_SEEDS.group(1)}")
    os.environ["COOP_TAG"] = _SEEDS.group(1)
import coop_v2 as V  # noqa: E402
from coop_bot import NEGATION  # noqa: E402
from timing_rule import ON_SIGNAL, OTHER  # noqa: E402
MAX_LEN = 64

# lines chosen to break a tokenizer port: whitespace runs, tabs, newlines, leading/trailing spaces,
# unicode (NFC-composed and decomposed accents, curly quotes, dashes, emoji, CJK, Cyrillic), digits,
# punctuation clusters, an over-long line that must be truncated, and the empty string
EDGE = [
    "", " ", "go", "  go  ", "breach\ton my\tgo", "come\nhere", "hold   the    other   angle",
    "don’t push yet", "“cover me”", "café", "cafe\u0301", "naïve flank", "rappel — now!!!",
    "go go go 🔥", "hold 左 angle", "прикрой меня", "2 left, 1 lit, 100 hp", "B-site... push???",
    "UPPERCASE BREACH NOW", "mIxEd CaSe FlAnK", "can't won't shouldn't", "x" * 200,
    " ".join(["push in and clear the room"] * 12), "smoke,flash,frag", "@#$%^&*()",
    # special tokens typed as text: the HF tokenizer matches them in the raw string as themselves
    "[CLS] breach now", "hold the [MASK] angle", "go[SEP]go", "[UNK]", "cover me [PAD]",
]


def main():
    os.makedirs(OUT, exist_ok=True)
    cfg = json.load(io.open(os.path.join(MODEL, "bot_config.json"), encoding="utf-8"))
    assert cfg.get("gate", "top") in ("top", "family"), cfg.get("gate")
    assert all(k in cfg["families"] for k in cfg["labels"]), "every label needs a family"
    dirs = [os.path.normpath(os.path.join(MODEL, m)) for m in cfg.get("members", ["."])]
    tok = AutoTokenizer.from_pretrained(dirs[0])   # the members share one tokenizer
    models = [] if CONFIG_ONLY else [AutoModelForSequenceClassification.from_pretrained(d, dtype=torch.float32).eval()
                                     for d in dirs]
    onnx_files = ["model.onnx"] if len(dirs) == 1 else [f"model{i}.onnx" for i in range(len(dirs))]

    # ---- vocabulary: tokenizer.json holds the Unigram model with scores
    tj = json.load(io.open(os.path.join(dirs[0], "tokenizer.json"), encoding="utf-8"))
    vocab = tj["model"]["vocab"]
    with io.open(os.path.join(OUT, "vocab.tsv"), "w", encoding="utf-8", newline="\n") as f:
        for piece, score in vocab:
            assert "\t" not in piece and "\n" not in piece, piece
            f.write(f"{piece}\t{score!r}\n")
    added = {a["content"]: a["id"] for a in tj["added_tokens"]}

    # ---- config for the interpreter
    json.dump({
        "labels": cfg["labels"], "families": cfg["families"], "phrases": cfg["phrases"],
        "threshold": cfg["threshold"], "gate": cfg.get("gate", "top"), "members": onnx_files, "max_len": MAX_LEN,
        "cls_id": added["[CLS]"], "sep_id": added["[SEP]"], "pad_id": added["[PAD]"],
        "unk_id": tj["model"]["unk_id"], "added_tokens": added,
        "regex": {"on_signal": ON_SIGNAL.pattern, "other": OTHER.pattern, "negation": NEGATION.pattern},
        # HOLD_FIRE (a v5 bot): "don't shoot" is an order, its leading negation must not cancel it (coop_bot.SAFE)
        "safe_intents": ["NONE", "WAIT", "HOLD_POSITION"] + (["HOLD_FIRE"] if "HOLD_FIRE" in cfg["labels"] else []),
        # the map's named places and the matcher's word lists (locations.json, validated by locations.py)
        "locations": {k: v for k, v in json.load(io.open(os.path.join(HERE, "locations.json"), encoding="utf-8")).items()
                      if not k.startswith("_")},
    }, io.open(os.path.join(OUT, "intent_config.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if CONFIG_ONLY:
        print(f"wrote {OUT}: intent_config.json and vocab.tsv only")
        return

    # ---- ONNX
    class Wrap(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_ids, attention_mask):
            return self.m(input_ids=input_ids, attention_mask=attention_mask).logits

    x = tok(["breach on my go", "come here"], padding=True, return_tensors="pt")
    for model, name in zip(models, onnx_files):
        torch.onnx.export(Wrap(model), (x["input_ids"], x["attention_mask"]), os.path.join(OUT, name),
                          input_names=["input_ids", "attention_mask"], output_names=["logits"],
                          dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"},
                                        "logits": {0: "batch"}},
                          opset_version=17, dynamo=False)
        # torch.onnx.export puts the wrapper back into its original mode afterwards, and a fresh Module
        # is in training mode -- so the model came out with dropout ON and the first golden file was
        # noise (found when ONNX Runtime matched a fresh PyTorch run exactly but not the golden file)
        model.eval()

    # ---- golden data: every study line (v1 and v2), every seed command, the probes, the edge cases;
    # probabilities are the members' average, as the bot computes them
    texts = ([i["text"] for i in V.load_items()] + [s["text"] for s in V.seed_items()] +
             [p["text"] for p in V.probe_items()] + EDGE)
    with io.open(os.path.join(OUT, "golden.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for t in texts:
            enc = tok([t], truncation=True, max_length=MAX_LEN, return_tensors="pt")
            with torch.no_grad():
                p = torch.stack([torch.softmax(m(**enc).logits[0], -1) for m in models]).mean(0).tolist()
            f.write(json.dumps({"text": t, "ids": enc["input_ids"][0].tolist(), "probs": p}, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}: {len(onnx_files)} ONNX model(s), vocab {len(vocab)} pieces, golden {len(texts)} lines")


if __name__ == "__main__":
    main()
