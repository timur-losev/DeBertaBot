"""Does Moonshine add a word ("Yeah", "You", "Okay") when a clip starts with silence? Same Kokoro clips, the
only thing varied is what comes before the first sound.    python lead_test.py VARIANT [N]"""
import io, json, os, re, sys, wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT, N = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 80
SRC = sys.argv[3] if len(sys.argv) > 3 else "wav_kokoro"
from moonshine_voice.moonshine_api import ModelArch
from moonshine_voice.transcriber import Transcriber
d = os.path.join(HERE, "models", "moonshine", "download.moonshine.ai", "model", "small-streaming-en", "quantized_26_08_21")
tr = Transcriber(model_path=d, model_arch=ModelArch.SMALL_STREAMING)
join = lambda t: " ".join(l.text.strip() for l in t.lines if l.text and l.text.strip())
W = lambda t: re.findall(r"[a-z0-9']+", t.lower())
rng = np.random.default_rng(0)
rows = json.load(io.open(os.path.join(HERE, "lines.json"), encoding="utf-8"))[:N]


def lead(kind):
    if kind == "none":
        return np.zeros(0, dtype=np.float32)
    secs, what = kind.split("-")
    n = int(float(secs) * 16000)
    return np.zeros(n, dtype=np.float32) if what == "zeros" else (rng.standard_normal(n) * 10 ** (-60 / 20)).astype(np.float32)


def streamed(x):
    st = tr.create_stream(); st.start()
    for b in range(0, len(x), 1600):
        st.add_audio(x[b:b + 1600].tolist(), 16000)
    st.stop()
    text = join(st.update_transcription(Transcriber.MOONSHINE_FLAG_FORCE_UPDATE)); st.close()
    return text


res = {"whole": [0, []], "live": [0, []]}
silence = []
for r in rows:
    with wave.open(os.path.join(HERE, SRC, r["wav"]), "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    first = int(np.argmax(np.abs(x) > 2e-3))
    silence.append(first / 16000)
    y = x if VARIANT == "asis" else np.concatenate([lead(VARIANT), x[first:]])
    ref = W(r["text"])
    for mode, text in (("whole", join(tr.transcribe_without_streaming(y.tolist(), 16000))), ("live", streamed(y))):
        h = W(text)
        if ref and len(h) >= 2 and h[0] != ref[0] and h[1] == ref[0]:
            res[mode][0] += 1; res[mode][1].append(h[0])
print(f"{SRC} {VARIANT:12s} n={len(rows)} | whole clip: {res['whole'][0]} extra first words {sorted(set(res['whole'][1]))} | "
      f"fed live: {res['live'][0]} {sorted(set(res['live'][1]))} | original leading silence: median {np.median(silence)*1000:.0f} ms")
