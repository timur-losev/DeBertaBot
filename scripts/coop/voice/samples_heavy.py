"""Samples of an accented Russian bot voice from the heavy models, for the owner to pick one before a whole corpus is
rendered. Two models, each in its own environment:

    venv_qw\\Scripts\\python samples_heavy.py qwen  <out>   Qwen3-TTS 1.7B VoiceDesign (Apache 2.0): a voice from words
    venv_cb\\Scripts\\python samples_heavy.py chatterbox <out>  Chatterbox Multilingual (MIT): the ISSAI voice cloned into
                                                             Russian, its accent carried over (cfg 0) or not

Writes <out>/<voice>_<n>.wav and <out>/<voice>.json (the settings)."""
import json
import os
import sys

import numpy as np
import soundfile as sf

try:
    import torch
except ImportError:   # samples_now.py takes LINES from here in the speech tools' Python, which has no torch
    torch = None

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "work", "refs")
LINES = ["Понял, брат.", "Иду за тобой, брат.", "Брат, контакт впереди, сверху!", "Какое окно? Справа, двадцать три метра?",
         "Спасибо, брат, стараюсь.", "Нормально всё, брат. Работаем.", "Не, брат. Респауна слишком долго ждать.",
         "Патроны кончились, перехожу на пистолет!"]

QWEN_VOICES = {
    "qw_uzbek": "A man of about thirty-five from Uzbekistan who speaks Russian as a second language, with a clear Uzbek accent: "
                "warm, slightly low baritone, relaxed and friendly, a little singsong Central Asian intonation, soft vowels.",
    "qw_tajik": "A middle-aged Tajik man with a deep, slightly husky voice, speaking Russian with a strong Tajik accent; "
                "calm, confident and kind, like an experienced soldier who has seen a lot.",
    "qw_kazakh": "A young Kazakh man in his late twenties, clear energetic baritone, speaking Russian with a light Kazakh "
                 "accent and Kazakh rhythm, cheerful and quick.",
    "qw_central": "A Central Asian migrant worker in his forties speaking broken but fluent street Russian with a heavy "
                  "Uzbek-Tajik accent, hard 'r', vowels a bit flattened, good-natured and humorous, medium-low voice.",
}


def qwen(out):
    from qwen_tts import Qwen3TTSModel
    model = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map="cuda:0", dtype=torch.bfloat16,
                                          attn_implementation="sdpa")
    for name, instruct in QWEN_VOICES.items():
        torch.manual_seed(7)
        wavs, sr = model.generate_voice_design(text=LINES, instruct=instruct, language="Russian")
        for n, wav in enumerate(wavs):
            sf.write(os.path.join(out, f"{name}_{n:02d}.wav"), np.asarray(wav, dtype=np.float32), sr)
        json.dump({"model": "Qwen3-TTS-12Hz-1.7B-VoiceDesign", "instruct": instruct, "seed": 7},
                  open(os.path.join(out, f"{name}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(name, "done", flush=True)


def no_watermark():
    """Perth's watermarker does not load on Windows (its class is None) and Chatterbox will not start without one: these
    clips only teach the Piper voice, so they go unmarked."""
    import perth
    if perth.PerthImplicitWatermarker is None:
        class Passthrough:
            def apply_watermark(self, wav, sample_rate):
                return wav
        perth.PerthImplicitWatermarker = Passthrough


def chatterbox(out):
    no_watermark()
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    voices = {
        "cb_kk_accent": ("kk_native.wav", 0.0, 0.5),   # Kazakh reference, no guidance: the Kazakh accent stays
        "cb_kk_accent_lively": ("kk_native.wav", 0.0, 0.7),
        "cb_kkru_accent": ("kk_as_ru.wav", 0.0, 0.5),  # the brat voice reading Russian as the reference
        "cb_kk_light": ("kk_native.wav", 0.3, 0.5),    # some guidance: a lighter accent
    }
    for name, (ref, cfg, exaggeration) in voices.items():
        for n, text in enumerate(LINES):
            torch.manual_seed(7)
            wav = model.generate(text, language_id="ru", audio_prompt_path=os.path.join(REFS, ref), cfg_weight=cfg,
                                 exaggeration=exaggeration)
            sf.write(os.path.join(out, f"{name}_{n:02d}.wav"), wav.squeeze(0).cpu().numpy(), model.sr)
        json.dump({"model": "chatterbox multilingual", "ref": ref, "cfg_weight": cfg, "exaggeration": exaggeration, "seed": 7},
                  open(os.path.join(out, f"{name}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(name, "done", flush=True)


if __name__ == "__main__":
    which, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    {"qwen": qwen, "chatterbox": chatterbox}[which](out)
