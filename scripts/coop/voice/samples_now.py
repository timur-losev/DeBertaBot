"""The current brat voice (Piper kk ISSAI, speaker 0, Kazakh rules reading Russian) on the sample lines of
samples_heavy.py, to compare against. Writes <out>/now_brat_<n>.wav and <out>/lines.json. Speech tools' Python."""
import json
import os
import sys
import wave

import numpy as np
import sherpa_onnx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from samples_heavy import LINES  # noqa: E402

d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stt", "tts", "vits-piper-kk_KZ-issai-high-as-ru")
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
onnx = [f for f in os.listdir(d) if f.endswith(".onnx")][0]
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(vits=sherpa_onnx.OfflineTtsVitsModelConfig(
    model=os.path.join(d, onnx), tokens=os.path.join(d, "tokens.txt"), data_dir=os.path.join(d, "espeak-ng-data")), num_threads=4)))
for n, text in enumerate(LINES):
    a = tts.generate(text, sid=0, speed=1.0)
    pcm = (np.clip(np.asarray(a.samples), -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(out, f"now_brat_{n:02d}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(a.sample_rate)
        w.writeframes(pcm.tobytes())
json.dump(LINES, open(os.path.join(out, "lines.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
