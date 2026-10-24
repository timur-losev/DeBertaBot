"""Reference clips for the heavy voice models: the Kazakh ISSAI Piper voice (CC BY 4.0, speaker 0, the voice the owner
picked for «брат») speaking Kazakh, and the same voice reading Russian with the Kazakh rules (the accent of the
current brat voice). Run with the speech tools' Python (scripts/coop/stt/venv)."""
import os
import sys
import wave

import numpy as np
import sherpa_onnx

TTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stt", "tts")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "work", "refs")
KAZAKH = ("Сәлеметсіз бе, менің атым Ерлан. Мен әскерде қызмет етемін. "
          "Бүгін ауа райы жақсы, біз тапсырманы орындауға дайынбыз, бауырым.")
RUSSIAN = "Понял, брат. Иду за тобой. Брат, контакт впереди, сверху! Нормально всё, работаем."
CLIPS = {"kk_native": ("vits-piper-kk_KZ-issai-high", KAZAKH), "kk_as_ru": ("vits-piper-kk_KZ-issai-high-as-ru", RUSSIAN)}

os.makedirs(OUT, exist_ok=True)
for name, (folder, text) in CLIPS.items():
    d = os.path.join(TTS, folder)
    onnx = [f for f in os.listdir(d) if f.endswith(".onnx")][0]
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(vits=sherpa_onnx.OfflineTtsVitsModelConfig(
        model=os.path.join(d, onnx), tokens=os.path.join(d, "tokens.txt"), data_dir=os.path.join(d, "espeak-ng-data")), num_threads=4)))
    a = tts.generate(text, sid=0, speed=1.0)
    pcm = (np.clip(np.asarray(a.samples), -1, 1) * 32767).astype(np.int16)
    path = os.path.join(OUT, f"{name}.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(a.sample_rate)
        w.writeframes(pcm.tobytes())
    with open(os.path.join(OUT, f"{name}.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{path}: {len(pcm) / a.sample_rate:.1f} s")
