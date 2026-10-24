"""Parakeet v3 hears rendered Russian lines back: the word errors per voice (samples) or per line (a corpus, to drop the
lines a heavy model got wrong before a Piper voice learns from them). Run with the speech tools' Python
(scripts/coop/stt/venv).

    python score_wavs.py samples <dir> <lines.json>    one row per voice prefix (<voice>_<nn>.wav, the lines in order)
    python score_wavs.py corpus <wav dir> <corpus.txt> <out.jsonl>   one row per line"""
import json
import os
import re
import sys

import numpy as np
import sherpa_onnx
import soundfile as sf
import soxr

STT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stt", "models", "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")


def words(t):
    t = t.lower().replace("ё", "е")
    return re.findall(r"[а-я0-9]+", t)


def wer(ref, hyp):
    r, h = words(ref), words(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)], max(len(r), 1)


def recognizer():
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=os.path.join(STT, "encoder.int8.onnx"), decoder=os.path.join(STT, "decoder.int8.onnx"),
        joiner=os.path.join(STT, "joiner.int8.onnx"), tokens=os.path.join(STT, "tokens.txt"), num_threads=6,
        model_type="nemo_transducer")


def hear(rec, path):
    audio, sr = sf.read(path, dtype="float32", always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        audio = soxr.resample(audio, sr, 16000)
    s = rec.create_stream()
    s.accept_waveform(16000, audio)
    rec.decode_stream(s)
    return s.result.text, len(audio) / 16000


def main():
    mode = sys.argv[1]
    rec = recognizer()
    if mode == "samples":
        folder, lines = sys.argv[2], json.load(open(sys.argv[3], encoding="utf-8"))
        voices = sorted({f.rsplit("_", 1)[0] for f in os.listdir(folder) if f.endswith(".wav") and f.rsplit("_", 1)[1][:-4].isdigit()})
        out = {}
        for v in voices:
            e = t = 0
            heard = []
            for n, text in enumerate(lines):
                path = os.path.join(folder, f"{v}_{n:02d}.wav")
                if not os.path.exists(path):
                    continue
                h, _ = hear(rec, path)
                x, y = wer(text, h)
                e, t = e + x, t + y
                heard.append(h)
            out[v] = {"wer": round(100 * e / max(t, 1), 1), "heard": heard}
            print(f"{v:22} {out[v]['wer']:5.1f}%  {heard[:2]}", flush=True)
        json.dump(out, open(os.path.join(folder, "scores.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    else:
        folder, corpus, out_path = sys.argv[2], sys.argv[3], sys.argv[4]
        with open(out_path, "w", encoding="utf-8") as out:
            for line in open(corpus, encoding="utf-8"):
                uid, text = line.rstrip("\n").split("|", 1)
                path = os.path.join(folder, uid + ".wav")
                if not os.path.exists(path):
                    continue
                h, secs = hear(rec, path)
                x, y = wer(text, h)
                out.write(json.dumps({"id": uid, "text": text, "heard": h, "errors": x, "words": y, "seconds": round(secs, 2)},
                                     ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
