"""The audio v54 adds (lists: export_v54.py), by the same voices and into the same folders as v4, v5, v51, v52 and v53 -- the file names differ:

  lines_v54.json  wav_kokoro, wav_kokorox (Kokoro English / other-language voices), wav_vctkA (training speakers),
                  wav_vctkB (speakers that only ever read test lines)
  seeds_v54.json  wav_seedkokoro, wav_seedkokorox, wav_seedvctkA
The Windows voices (wav_clean, wav_seedclean) come from synth_windows_v54.ps1.
The voices are dealt on from where v53 stopped (722 lines, 1146 seed commands), so the pools stay the same and no voice
is over-used. 16 kHz mono WAV, 0.2 s of silence on both sides; voices_v54.json records who read what.
"""
import io, json, os, re, time, wave

import numpy as np
import sherpa_onnx
import soxr

HERE = os.path.dirname(os.path.abspath(__file__))
lines = json.load(io.open(os.path.join(HERE, "lines_v54.json"), encoding="utf-8"))
seeds = json.load(io.open(os.path.join(HERE, "seeds_v54.json"), encoding="utf-8"))
N_LINES, N_SEEDS = 722, 1146         # what v4, v5, v51, v52 and v53 voiced
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
    pool = {"A": {g: groups[g][0::2] for g in names}, "B": {g: groups[g][1::2] for g in names}}     # as synth_train.py
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=os.path.join(d, "en_GB-vctk-medium.onnx"), lexicon="",
                                                   tokens=os.path.join(d, "tokens.txt"), data_dir=os.path.join(d, "espeak-ng-data")),
        num_threads=4, provider="cpu")))
    for folder, rows, p, base in (("wav_vctkA", lines, "A", N_LINES), ("wav_vctkB", lines, "B", N_LINES),
                                  ("wav_seedvctkA", seeds, "A", N_SEEDS)):
        for n, r in enumerate(rows, base):
            g = names[n % len(names)]
            spk = pool[p][g][(n // len(names)) % len(pool[p][g])]
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
    for rows, base, en, fo in ((lines, N_LINES, "wav_kokoro", "wav_kokorox"), (seeds, N_SEEDS, "wav_seedkokoro", "wav_seedkokorox")):
        for n, r in enumerate(rows, base):
            for folder, v in ((en, english[n % len(english)]), (fo, foreign[n % len(foreign)])):
                a = tts.generate(r["text"], sid=voices.index(v), speed=1.0)
                save(folder, r["wav"], a.samples, a.sample_rate)
                meta.setdefault(folder, {})[r["id"]] = {"voice": v}
        print(en, fo, "done", flush=True)


t0 = time.time()
vctk(); print(f"vctk {time.time() - t0:.0f}s", flush=True)
kokoro(); print(f"kokoro {time.time() - t0:.0f}s", flush=True)
json.dump(meta, io.open(os.path.join(HERE, "voices_v54.json"), "w", encoding="utf-8"), indent=0)
