"""One speech-to-text engine over the synthesized lines, as push-to-talk would use it.

    python run_stt.py ENGINE CONDITION [--limit N]      # CONDITION: clean | noisy

Per clip it records the text and two delays:
  full   the whole clip handed over at once after the key is released (nothing was computed while it was held)
  tail   streaming engines only: audio fed in 100 ms pieces while the key is held, then the time from the last
         piece to the final text
and per engine the memory after loading and the CPU time used per wall second (how many cores it keeps busy).
"""
import io, json, os, sys, time, wave

import numpy as np
import psutil

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(HERE, "models")
ENGINE, COND = sys.argv[1], sys.argv[2]
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
STREAM_N = int(sys.argv[sys.argv.index("--stream-n") + 1]) if "--stream-n" in sys.argv else 60
TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
LIVE = bool(os.environ.get("STT_LIVE"))
THREADS = int(os.environ.get("STT_THREADS", "2"))
CHUNK = 1600          # 100 ms at 16 kHz
proc = psutil.Process()
# the game's words, for the engines that can be told which words to expect
TERMS = ["breach", "rappel", "frag", "flash", "smoke", "drone", "defuse", "plant", "flank", "vault", "revive",
         "nade", "flashbang", "stairs", "basement", "roof", "window", "door", "on my go", "on my mark",
         "fall back", "cover me", "hold the angle", "push in", "take cover", "defuser", "hatch", "barricade"]


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2, path
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0


def sherpa_online(d, enc, dec, joi, hotwords=False):
    import sherpa_onnx
    kw = dict(tokens=os.path.join(d, "tokens.txt"), encoder=os.path.join(d, enc), decoder=os.path.join(d, dec),
              joiner=os.path.join(d, joi), num_threads=THREADS, sample_rate=16000, feature_dim=80, provider="cpu")
    if hotwords:
        hw = os.path.join(HERE, "hotwords.txt")
        io.open(hw, "w", encoding="utf-8").write("\n".join(t.upper() for t in TERMS) + "\n")
        kw.update(decoding_method="modified_beam_search", hotwords_file=hw, hotwords_score=2.0,
                  modeling_unit="bpe", bpe_vocab=os.path.join(d, "bpe.vocab"))
    else:
        kw.update(decoding_method="greedy_search")
    rec = sherpa_onnx.OnlineRecognizer.from_transducer(**kw)
    tail_pad = np.zeros(int(float(os.environ.get("STT_TAIL", "0.5")) * 16000), dtype=np.float32)   # the model's right context has to be flushed

    def finish(s):
        s.accept_waveform(16000, tail_pad)
        s.input_finished()
        while rec.is_ready(s):
            rec.decode_stream(s)
        return rec.get_result(s)

    def full(x):
        s = rec.create_stream()
        s.accept_waveform(16000, x)
        return finish(s)

    def streamed(x):
        s = rec.create_stream()
        busy = 0.0
        for b in range(0, len(x), CHUNK):
            t = time.perf_counter()
            s.accept_waveform(16000, x[b:b + CHUNK])
            while rec.is_ready(s):
                rec.decode_stream(s)
            busy += time.perf_counter() - t
        t = time.perf_counter()
        text = finish(s)
        return text, time.perf_counter() - t, busy
    return full, streamed


def sherpa_offline(kind, d):
    import sherpa_onnx
    if kind == "nemo_ctc":
        rec = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(model=os.path.join(d, "model.int8.onnx"),
                                                          tokens=os.path.join(d, "tokens.txt"), num_threads=THREADS)
    elif kind == "nemo_transducer":
        rec = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=os.path.join(d, "encoder.int8.onnx"), decoder=os.path.join(d, "decoder.int8.onnx"),
            joiner=os.path.join(d, "joiner.int8.onnx"), tokens=os.path.join(d, "tokens.txt"),
            num_threads=THREADS, model_type="nemo_transducer")
    else:
        rec = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=os.path.join(d, "tiny.en-encoder.int8.onnx"), decoder=os.path.join(d, "tiny.en-decoder.int8.onnx"),
            tokens=os.path.join(d, "tiny.en-tokens.txt"), language="en", task="transcribe", num_threads=THREADS)

    def full(x):
        s = rec.create_stream()
        s.accept_waveform(16000, x)
        rec.decode_stream(s)
        return s.result.text
    return full, None


def moonshine(arch_name, keyterms=False):
    from moonshine_voice.moonshine_api import ModelArch
    from moonshine_voice.transcriber import Transcriber
    arch = getattr(ModelArch, arch_name)
    d = os.path.join(M, "moonshine", "download.moonshine.ai", "model",
                     f"{arch_name.split('_')[0].lower()}-streaming-en", "quantized_26_08_21")
    tr = Transcriber(model_path=d, model_arch=arch)
    if keyterms:
        tr.set_keyterms(TERMS)
    join = lambda t: " ".join(l.text.strip() for l in t.lines if l.text and l.text.strip())

    def full(x):
        return join(tr.transcribe_without_streaming(x.tolist(), 16000))

    def streamed(x):
        st = tr.create_stream()
        st.start()
        busy = 0.0
        for b in range(0, len(x), CHUNK):
            t = time.perf_counter()
            st.add_audio(x[b:b + CHUNK].tolist(), 16000)
            busy += time.perf_counter() - t
        t = time.perf_counter()
        st.stop()
        text = join(st.update_transcription(Transcriber.MOONSHINE_FLAG_FORCE_UPDATE))
        dt = time.perf_counter() - t
        st.close()
        return text, dt, busy
    return full, streamed


Z23 = "epoch-99-avg-1-chunk-16-left-128"
BUILD = {
    "moonshine-tiny": lambda: moonshine("TINY_STREAMING"),
    "moonshine-small": lambda: moonshine("SMALL_STREAMING"),
    "moonshine-medium": lambda: moonshine("MEDIUM_STREAMING"),
    "moonshine-small+terms": lambda: moonshine("SMALL_STREAMING", keyterms=True),
    "zipformer-kroko25": lambda: sherpa_online(os.path.join(M, "sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06"),
                                               "encoder.onnx", "decoder.onnx", "joiner.onnx"),
    "zipformer-2023": lambda: sherpa_online(os.path.join(M, "sherpa-onnx-streaming-zipformer-en-2023-06-26"),
                                            f"encoder-{Z23}.int8.onnx", f"decoder-{Z23}.onnx", f"joiner-{Z23}.int8.onnx"),
    "zipformer-2023+terms": lambda: sherpa_online(os.path.join(M, "sherpa-onnx-streaming-zipformer-en-2023-06-26"),
                                                  f"encoder-{Z23}.int8.onnx", f"decoder-{Z23}.onnx",
                                                  f"joiner-{Z23}.int8.onnx", hotwords=True),
    "parakeet-110m": lambda: sherpa_offline("nemo_ctc", os.path.join(M, "sherpa-onnx-nemo-parakeet_tdt_ctc_110m-en-36000-int8")),
    "parakeet-0.6b-v2": lambda: sherpa_offline("nemo_transducer", os.path.join(M, "sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8")),
    "whisper-tiny.en": lambda: sherpa_offline("whisper", os.path.join(M, "sherpa-onnx-whisper-tiny.en")),
}

rows = json.load(io.open(os.path.join(HERE, os.environ.get("STT_LINES", "lines.json")), encoding="utf-8"))[:LIMIT]
rss0 = proc.memory_info().rss
t0 = time.perf_counter()
full, streamed = BUILD[ENGINE]()
load_s = time.perf_counter() - t0
warm = read_wav(os.path.join(HERE, f"wav_{COND}", rows[0]["wav"]))
full(warm)
if streamed:
    streamed(warm)
rss_loaded = proc.memory_info().rss
out, audio_s = [], 0.0
cpu0, wall0 = sum(proc.cpu_times()[:2]), time.perf_counter()
for r in rows:
    x = read_wav(os.path.join(HERE, f"wav_{COND}", r["wav"]))
    audio_s += len(x) / 16000
    t = time.perf_counter()
    text = streamed(x)[0] if LIVE else full(x)
    rec = {"id": r["id"], "text": text, "full_ms": (time.perf_counter() - t) * 1000, "audio_s": len(x) / 16000}
    if streamed and len(out) < STREAM_N:
        text2, tail, busy = streamed(x)
        rec.update(text_streamed=text2, tail_ms=tail * 1000, busy_ms=busy * 1000)
    out.append(rec)
cpu, wall = sum(proc.cpu_times()[:2]) - cpu0, time.perf_counter() - wall0
med = lambda k: float(np.median([o[k] for o in out if k in o])) if any(k in o for o in out) else None
p95 = lambda k: float(np.percentile([o[k] for o in out if k in o], 95)) if any(k in o for o in out) else None
summary = {"engine": ENGINE, "cond": COND, "n": len(out), "load_s": load_s, "rss_mb": (rss_loaded - rss0) / 2**20,
           "peak_mb": getattr(proc.memory_info(), "peak_wset", 0) / 2**20, "cores_busy": cpu / wall,
           "audio_s_avg": audio_s / len(out), "full_ms_med": med("full_ms"), "full_ms_p95": p95("full_ms"),
           "tail_ms_med": med("tail_ms"), "tail_ms_p95": p95("tail_ms"),
           "rtf_streamed": (sum(o["busy_ms"] + o["tail_ms"] for o in out if "tail_ms" in o) / 1000 / sum(o["audio_s"] for o in out if "tail_ms" in o)) if streamed and STREAM_N else None,
           "same_text_streamed": (sum(o["text"].strip().lower() == o["text_streamed"].strip().lower() for o in out if "tail_ms" in o) / max(1, sum("tail_ms" in o for o in out))) if streamed and STREAM_N else None,
           "threads": os.environ.get("MOONSHINE_ORT_SINGLE_THREAD") and "1" or (ENGINE.startswith("moonshine") and "all" or str(THREADS))}
json.dump({"summary": summary, "rows": out}, io.open(os.path.join(HERE, f"out_{ENGINE}{'-live' if LIVE else ''}_{COND}{TAG}.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print(json.dumps({k: (round(v, 2) if isinstance(v, float) else v) for k, v in summary.items()}))
for o in out[:4]:
    print("   ", repr(o["text"]), "|", repr(o.get("text_streamed")))
