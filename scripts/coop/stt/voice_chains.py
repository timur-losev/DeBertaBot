"""Voices for the chain lines (chains/, chains2/): a line is read by a synthesized voice and heard by Parakeet TDT 0.6B v2,
as the classifier's lines are (synth_v54.py, run_stt.py), with the same voice pools; the audio is not kept. Only the r6
and cs lines are read: an stt line is written as a transcript already, as in the classifier's data.

    venv\\Scripts\\python voice_chains.py VOICES OUT.json IN.json [IN.json ...]
        IN.json   lists of rows with "id", "voice" and "text". A context item (chains2/ctx_*.json: "line", "before")
                  is read as its line (id) and its earlier lines (id#b0, id#b1)
        VOICES    train:  one VCTK pool-A speaker and one Kokoro English voice per line (conditions vctkA, kokoro)
                  train2: another pool-A speaker and a Kokoro voice of another language (vctkA2, kokorox)
                  test:   one VCTK pool-B speaker per line, the speakers that only ever read test lines (vctkB)
                  test3:  three different pool-B speakers per line (vctkB, vctkB2, vctkB3)
        OUT.json  {condition: {id: transcript}}: lowercased, the final .!? stripped, as build_v54.norm does

Runs in the speech tools' environment (requirements.txt), at idle priority on a few threads.
"""
import ctypes, io, json, os, re, sys, time

import numpy as np
import sherpa_onnx
import soxr

HERE = os.path.dirname(os.path.abspath(__file__))
if os.name == "nt":
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)     # IDLE_PRIORITY_CLASS
PAD = np.zeros(int(0.2 * 16000), dtype=np.float32)
norm = lambda t: re.sub(r"[.!?]+$", "", t.strip()).lower()  # noqa: E731


def clip(samples, sr):
    """16 kHz, peak 0.7, 0.2 s of silence on both sides, through 16 bits: what synth_v54.save writes and run_stt.read_wav reads."""
    x = soxr.resample(np.asarray(samples, dtype=np.float32), sr, 16000)
    x = np.concatenate([PAD, x / max(1e-6, np.abs(x).max()) * 0.7, PAD])
    return (np.clip(x, -1, 1) * 32767).astype(np.int16).astype(np.float32) / 32768.0


def vctk(pool_name, shift=0):
    """shift: deal the speakers from another place, so the same line gets another speaker of the pool."""
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
    pool = {g: groups[g][0::2] if pool_name == "A" else groups[g][1::2] for g in names}     # as synth_train.py
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=os.path.join(d, "en_GB-vctk-medium.onnx"), lexicon="",
                                                   tokens=os.path.join(d, "tokens.txt"), data_dir=os.path.join(d, "espeak-ng-data")),
        num_threads=4, provider="cpu")))

    def say(n, text):
        n += shift
        g = names[n % len(names)]
        a = tts.generate(text, sid=sid[pool[g][(n // len(names)) % len(pool[g])]], speed=1.0)
        return clip(a.samples, a.sample_rate)
    return say


def kokoro(foreign=False):
    d = os.path.join(HERE, "tts", "kokoro-multi-lang-v1_0")
    voices = re.search(rb"af_alloy(?:,[a-z]{2}_[a-z0-9]+)+", open(os.path.join(d, "model.onnx"), "rb").read()).group(0).decode().split(",")
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=os.path.join(d, "model.onnx"), voices=os.path.join(d, "voices.bin"), tokens=os.path.join(d, "tokens.txt"),
            data_dir=os.path.join(d, "espeak-ng-data"), dict_dir=os.path.join(d, "dict"),
            lexicon=os.path.join(d, "lexicon-us-en.txt") + "," + os.path.join(d, "lexicon-zh.txt")),
        num_threads=4, provider="cpu")))
    some = [v for v in voices if (v[0] not in "ab") == foreign]     # a..., b...: the English voices, as synth_v54.py

    def say(n, text):
        a = tts.generate(text, sid=voices.index(some[n % len(some)]), speed=1.0)
        return clip(a.samples, a.sample_rate)
    return say


def parakeet():
    d = os.path.join(HERE, "models", "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8")
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=os.path.join(d, "encoder.int8.onnx"), decoder=os.path.join(d, "decoder.int8.onnx"),
        joiner=os.path.join(d, "joiner.int8.onnx"), tokens=os.path.join(d, "tokens.txt"), num_threads=2, model_type="nemo_transducer")

    def hear(x):
        s = rec.create_stream()
        s.accept_waveform(16000, x)
        rec.decode_stream(s)
        return s.result.text
    return hear


if __name__ == "__main__":
    which, out_path = sys.argv[1], sys.argv[2]
    rows = []
    for p in sys.argv[3:]:
        for r in json.load(io.open(p, encoding="utf-8")):
            if r["voice"] not in ("r6", "cs"):
                continue
            if "line" in r:
                rows.append({"id": r["id"], "text": r["line"]})
                rows += [{"id": f"{r['id']}#b{k}", "text": b} for k, b in enumerate(r["before"])]
            else:
                rows.append({"id": r["id"], "text": r["text"]})
    conds = {"train": [("vctkA", lambda: vctk("A")), ("kokoro", kokoro)],
             "train2": [("vctkA2", lambda: vctk("A", 5)), ("kokorox", lambda: kokoro(True))],
             "test": [("vctkB", lambda: vctk("B"))],
             "test3": [("vctkB", lambda: vctk("B")), ("vctkB2", lambda: vctk("B", 5)), ("vctkB3", lambda: vctk("B", 11))]}[which]
    hear = parakeet()
    out = json.load(io.open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    t0 = time.time()
    for cond, make in conds:
        done = out.setdefault(cond, {})
        say = make()
        for n, r in enumerate(rows):
            if r["id"] not in done:
                done[r["id"]] = norm(hear(say(n, r["text"])))
        json.dump(out, io.open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(f"{cond}: {len(rows)} lines, {time.time() - t0:.0f}s", flush=True)
