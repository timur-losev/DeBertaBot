"""The 422 test lines spoken by neural voices with known accents (all offline, through sherpa-onnx):

  wav_vctk     Piper VITS trained on VCTK: 107 real speakers, their accent from the corpus's speaker list.
               Lines are dealt round-robin over accent groups, so every group gets about the same number.
  wav_kokoro   Kokoro v1.0, the 28 English voices (American and British)
  wav_kokorox  Kokoro v1.0, voices recorded for other languages (Spanish, French, Hindi, Italian, Japanese,
               Portuguese, Mandarin) reading the English lines: a foreign voice, not a measured accent

Output: 16 kHz mono 16-bit WAV with 0.2 s of silence on both sides, and accents.json (line id -> voice, group).
"""
import io, json, os, re, sys, time, wave

import numpy as np
import sherpa_onnx
import soxr

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(io.open(os.path.join(HERE, "lines.json"), encoding="utf-8"))
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
            info["p" + p[0]] = (p[3], p[2], " ".join(p[4:]))
    merge = {"Welsh": "English", "NewZealand": "Australian/NZ", "Australian": "Australian/NZ", "NorthernIrish": "Northern Irish",
             "SouthAfrican": "South African"}
    groups = {}
    for spk in sorted(sid):
        if spk in info:
            groups.setdefault(merge.get(info[spk][0], info[spk][0]), []).append(spk)
    names = sorted(groups)
    print("vctk groups:", {g: len(groups[g]) for g in names}, flush=True)
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=os.path.join(d, "en_GB-vctk-medium.onnx"), lexicon="",
                                                   tokens=os.path.join(d, "tokens.txt"), data_dir=os.path.join(d, "espeak-ng-data")),
        num_threads=4, provider="cpu")))
    used = {g: 0 for g in names}
    for n, r in enumerate(rows):
        g = names[n % len(names)]
        spk = groups[g][used[g] % len(groups[g])]; used[g] += 1
        a = tts.generate(r["text"], sid=sid[spk], speed=1.0)
        save("wav_vctk", r["wav"], a.samples, a.sample_rate)
        meta.setdefault(r["id"], {})["vctk"] = {"voice": spk, "group": g, "gender": info[spk][1], "region": info[spk][2]}


def kokoro():
    d = os.path.join(HERE, "tts", "kokoro-multi-lang-v1_0")
    raw = open(os.path.join(d, "model.onnx"), "rb").read()
    m = re.search(rb"af_alloy(?:,[a-z]{2}_[a-z0-9]+)+", raw)
    voices = m.group(0).decode().split(",")
    print("kokoro voices:", len(voices), voices[:4], "...", voices[-3:], flush=True)
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=os.path.join(d, "model.onnx"), voices=os.path.join(d, "voices.bin"), tokens=os.path.join(d, "tokens.txt"),
            data_dir=os.path.join(d, "espeak-ng-data"), dict_dir=os.path.join(d, "dict"),
            lexicon=os.path.join(d, "lexicon-us-en.txt") + "," + os.path.join(d, "lexicon-zh.txt")),
        num_threads=6, provider="cpu")))
    lang = {"a": "American", "b": "British", "e": "Spanish voice", "f": "French voice", "h": "Hindi voice", "i": "Italian voice",
            "j": "Japanese voice", "p": "Portuguese voice", "z": "Mandarin voice"}
    english = [v for v in voices if v[0] in "ab"]
    foreign = {}
    for v in voices:
        if v[0] not in "ab":
            foreign.setdefault(lang[v[0]], []).append(v)
    fnames = sorted(foreign)
    used = {g: 0 for g in fnames}
    for n, r in enumerate(rows):
        v = english[n % len(english)]
        a = tts.generate(r["text"], sid=voices.index(v), speed=1.0)
        save("wav_kokoro", r["wav"], a.samples, a.sample_rate)
        meta.setdefault(r["id"], {})["kokoro"] = {"voice": v, "group": lang[v[0]], "gender": v[1].upper()}
        g = fnames[n % len(fnames)]
        v = foreign[g][used[g] % len(foreign[g])]; used[g] += 1
        a = tts.generate(r["text"], sid=voices.index(v), speed=1.0)
        save("wav_kokorox", r["wav"], a.samples, a.sample_rate)
        meta[r["id"]]["kokorox"] = {"voice": v, "group": g, "gender": v[1].upper()}


t0 = time.time()
vctk(); print(f"vctk done, {time.time() - t0:.0f}s", flush=True)
kokoro(); print(f"kokoro done, {time.time() - t0:.0f}s", flush=True)
json.dump(meta, io.open(os.path.join(HERE, "accents.json"), "w", encoding="utf-8"), indent=0)
