"""A trained Piper voice as a sherpa-onnx voice folder, the way the game's brain loads it (<brain>/voice_<lang>_<persona>):
the model with sherpa's metadata, tokens.txt from the voice's phoneme map, the espeak-ng data of an existing ru voice.

    python to_sherpa.py <model.onnx> <config.json> <out dir> [--name ru_RU-brat-medium]

Run with the Piper training Python (it has onnx)."""
import argparse
import json
import os
import shutil

import onnx

HERE = os.path.dirname(os.path.abspath(__file__))
ESPEAK = os.path.join(HERE, "..", "stt", "tts", "vits-piper-ru_RU-denis-medium", "espeak-ng-data")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("config")
    ap.add_argument("out")
    ap.add_argument("--name", default="ru_RU-brat-medium")
    ap.add_argument("--card", default="")
    args = ap.parse_args()
    config = json.load(open(args.config, encoding="utf-8"))
    os.makedirs(args.out, exist_ok=True)

    model = onnx.load(args.model)
    meta = {"model_type": "vits", "comment": "piper", "language": "Russian", "voice": config["espeak"]["voice"],
            "has_espeak": "1", "n_speakers": str(config.get("num_speakers", 1)), "sample_rate": str(config["audio"]["sample_rate"])}
    del model.metadata_props[:]
    for k, v in meta.items():
        p = model.metadata_props.add()
        p.key, p.value = k, v
    onnx.save(model, os.path.join(args.out, args.name + ".onnx"))
    json.dump(config, open(os.path.join(args.out, args.name + ".onnx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    with open(os.path.join(args.out, "tokens.txt"), "w", encoding="utf-8") as f:
        for symbol, ids in sorted(config["phoneme_id_map"].items(), key=lambda kv: kv[1][0]):
            # piper1-gpl's map also has English diphthongs as single tokens ("aɪ"); espeak's Russian never makes them,
            # and sherpa reads one codepoint per token
            if len(symbol) == 1:
                f.write(f"{symbol} {ids[0]}\n")
    target = os.path.join(args.out, "espeak-ng-data")
    if not os.path.isdir(target):
        shutil.copytree(ESPEAK, target)
    if args.card:
        shutil.copy(args.card, os.path.join(args.out, "MODEL_CARD"))
    print("sherpa voice ->", args.out, meta)


if __name__ == "__main__":
    main()
