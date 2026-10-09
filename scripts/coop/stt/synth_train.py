"""Audio for training the bot on Parakeet's output, and for testing it on speakers it never heard.

The VCTK speakers of every accent group are split in two halves:
  pool A   training voices:  wav_vctkA (the 422 lines), wav_seedvctkA (the 580 seed commands)
  pool B   test voices only: wav_vctkB (the 422 lines)
The seed commands are also read by the Kokoro voices (wav_seedkokoro: English voices, wav_seedkokorox: voices
recorded for other languages). 16 kHz mono WAV, 0.2 s of silence on both sides. voices_train.json records who read what.
"""
import io, json, os, re, sys, time, wave

import numpy as np
import sherpa_onnx
import soxr

HERE = os.path.dirname(os.path.abspath(__file__))
lines = json.load(io.open(os.path.join(HERE, "lines.json"), encoding="utf-8"))
seeds = json.load(io.open(os.path.join(HERE, "seeds.json"), encoding="utf-8"))
PAD = np.zeros(int(0.2 * 16000), dtype=np.float32)
meta = {}


def save(folder, name, samples, sr):
    x = soxr.resample(np.asarray(samples, dtype=np.float32), sr, 16000)
    x = np.concatenate([PAD, x / max(1e-6, np.abs(x).max()) * 0.7, PAD])
    os.makedirs(os.path.join(HERE, folder), exist_ok=True)
    with wave.open(os.path.join(HERE, folder, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def vctk():
    d = os.path.join(HERE, "tts", "vits-piper-en_GB-vctk-medium")
    sid = json.load(io.open(os.path.join(d, "en_GB-vctk-medium.onnx.json"), encoding="utf-8"))["speaker_id_map"]
    info = {}
    for l in io.open(os.path.join(HERE, "speaker-info.txt"), encoding="utf-8").read().splitlines()[1:]:
        p = l.split()
        if len(p) >= 4:
            info["p" + p[0]] = p[3]
    merge = {"Welsh": "English", "NewZealand": "Australian/NZ", "Australian": "Australian/NZ", "NorthernIrish": "Northern Irish",
             "SouthAfrican": "South African"}
    groups = {}
    for spk in sorted(sid):
        if spk in info:
            groups.setdefault(merge.get(info[spk], info[spk]), []).append(spk)
    names = sorted(groups)
    pool = {"A": {g: groups[g][0::2] for g in names}, "B": {g: groups[g][1::2] for g in names}}
    print("vctk pool sizes:", {p: sum(len(v) for v in pool[p].values()) for p in pool}, flush=True)
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=os.path.join(d, "en_GB-vctk-medium.onnx"), lexicon="",
                                                   tokens=os.path.join(d, "tokens.txt"), data_dir=os.path.join(d, "espeak-ng-data")),
        num_threads=4, provider="cpu")))
    for folder, rows, p in (("wav_vctkA", lines, "A"), ("wav_vctkB", lines, "B"), ("wav_seedvctkA", seeds, "A")):
        used = {g: 0 for g in names}
        for n, r in enumerate(rows):
            g = names[n % len(names)]
            spk = pool[p][g][used[g] % len(pool[p][g])]; used[g] += 1
            a = tts.generate(r["text"], sid=sid[spk], speed=1.0)
            save(folder, r["wav"], a.samples, a.sample_rate)
            meta.setdefault(folder, {})[r["id"]] = {"voice": spk, "group": g}
        print(folder, "done", flush=True)


def kokoro():
    d = os.path.join(HERE, "tts", "kokoro-multi-lang-v1_0")
    voices = re.search(rb"af_alloy(?:,[a-z]{2}_[a-z0-9]+)+", open(os.path.join(d, "model.onnx"), "rb").read()).group(0).decode().split(",")
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=os.path.join(d, "model.onnx"), voices=os.path.join(d, "voices.bin"), tokens=os.path.join(d, "tokens.txt"),
            data_dir=os.path.join(d, "espeak-ng-data"), dict_dir=os.path.join(d, "dict"),
            lexicon=os.path.join(d, "lexicon-us-en.txt") + "," + os.path.join(d, "lexicon-zh.txt")),
        num_threads=8, provider="cpu")))
    english = [v for v in voices if v[0] in "ab"]
    foreign = [v for v in voices if v[0] not in "ab"]
    for n, r in enumerate(seeds):
        for folder, v in (("wav_seedkokoro", english[n % len(english)]), ("wav_seedkokorox", foreign[n % len(foreign)])):
            a = tts.generate(r["text"], sid=voices.index(v), speed=1.0)
            save(folder, r["wav"], a.samples, a.sample_rate)
            meta.setdefault(folder, {})[r["id"]] = {"voice": v}
    print("kokoro seed sets done", flush=True)


t0 = time.time()
vctk(); print(f"vctk {time.time() - t0:.0f}s", flush=True)
kokoro(); print(f"kokoro {time.time() - t0:.0f}s", flush=True)
json.dump(meta, io.open(os.path.join(HERE, "voices_train.json"), "w", encoding="utf-8"), indent=0)
