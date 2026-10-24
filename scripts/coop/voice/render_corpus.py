"""Renders the training corpus (make_corpus.py) in one heavy-model voice, for a Piper voice to learn from.

    venv_cb\\Scripts\\python render_corpus.py chatterbox --ref work/refs/kk_native.wav --cfg 0 --exaggeration 0.5 \\
        --corpus work/brat/corpus.txt --out work/brat/wav
    venv_qw\\Scripts\\python render_corpus.py qwen-clone --ref work/samples/qw_uzbek_ref.wav --ref-text "..." \\
        --corpus work/brat/corpus.txt --out work/brat/wav

qwen-clone: Qwen3-TTS Base clones one VoiceDesign clip (in-context, with its words), so every line has the same voice;
VoiceDesign itself draws a new voice per call. Resumable: a line whose wav exists is skipped. Each line is seeded by its
index, so a rerun gives the same audio."""
import argparse
import os
import time

import numpy as np
import soundfile as sf
import torch


def lines_of(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if "|" in line:
            uid, text = line.split("|", 1)
            out.append((uid, text))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=["chatterbox", "qwen-clone"])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--ref-text", default="")
    ap.add_argument("--cfg", type=float, default=0.0)
    ap.add_argument("--exaggeration", type=float, default=0.5)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    todo = [(i, uid, text) for i, (uid, text) in enumerate(lines_of(args.corpus))
            if not os.path.exists(os.path.join(args.out, uid + ".wav"))]
    print(f"{len(todo)} lines to render", flush=True)
    start = time.time()

    if args.model == "chatterbox":
        from samples_heavy import no_watermark
        no_watermark()
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
        model.prepare_conditionals(args.ref, exaggeration=args.exaggeration)
        for k, (i, uid, text) in enumerate(todo):
            torch.manual_seed(i)
            wav = model.generate(text, language_id="ru", cfg_weight=args.cfg, exaggeration=args.exaggeration,
                                 temperature=args.temperature)
            sf.write(os.path.join(args.out, uid + ".wav"), wav.squeeze(0).cpu().numpy(), model.sr)
            if k % 50 == 0:
                print(f"{k}/{len(todo)} {time.time() - start:.0f} s", flush=True)
    else:
        from qwen_tts import Qwen3TTSModel
        model = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cuda:0", dtype=torch.bfloat16,
                                              attn_implementation="sdpa")
        prompt = model.create_voice_clone_prompt(ref_audio=args.ref, ref_text=args.ref_text)
        for k in range(0, len(todo), args.batch):
            chunk = todo[k:k + args.batch]
            torch.manual_seed(chunk[0][0])
            wavs, sr = model.generate_voice_clone(text=[t for _, _, t in chunk], language="Russian",
                                                  voice_clone_prompt=prompt * len(chunk))
            for (i, uid, _), wav in zip(chunk, wavs):
                sf.write(os.path.join(args.out, uid + ".wav"), np.asarray(wav, dtype=np.float32), sr)
            print(f"{k + len(chunk)}/{len(todo)} {time.time() - start:.0f} s", flush=True)
    print(f"done in {time.time() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main()
