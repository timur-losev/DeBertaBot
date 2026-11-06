"""The deployed brain (Binaries/CoopBrainV6) started with the game's arguments (Russian: the bro persona and its voice; English:
the plain voice), without a memory file: RAM (working set) and the GPU's memory after the start, then N recorded lines of
synthetic voices (stt/wav_ru or stt/wav_clean) through the whole brain ("wav") and the reply's first sentence as voice ("say"
with "stream"): the time from the end of the clip to the reply and to the first audio. Decoder on the GPU (as in the game)
or on the CPU (--decoder-cpu). README.md, "Measured results". The GPU's memory is the card's total, so other programs move it.

    python measure_brain_cost.py gpu|cpu [N] [ru|en]
"""
import glob, io, json, os, subprocess, sys, time
import psutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import memory_tests as mt

B = r"J:\UE4\Projects\LyraStarterGame58\Binaries\CoopBrainV6"
mode = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
lang = sys.argv[3] if len(sys.argv) > 3 else "ru"
args = [B + r"\coop_cli.exe", "--serve", "--model-dir", B + r"\bot", "--threads", "1", "--no-spin",
        "--stt-model", B + r"\stt_v3", "--stt-threads", "2", "--vad", B + r"\vad\silero_vad.onnx",
        "--tts", "--tts-piper", B + r"\voice", "--tts-speed", "1.00", "--tts-speaker", "p311", "--tts-provider", "cpu",
        "--tts-threads", "4", "--chain", B + r"\chain", "--decoder-threads", "4",
        "--replies-bro", B + r"\replies\replies_ru_brat.json", "--bro", "on", "--bro-relapse", "30", "--language", "ru",
        "--replies", B + r"\replies\replies_ru.json", "--voice-local", B + r"\voice_ru_brat"]
if mode == "cpu":
    args += ["--decoder-cpu"]
if lang == "en":
    cut = args.index("--replies-bro")
    args = args[:cut]


def gpu_used():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True)
    return int(out.stdout.strip().splitlines()[0])


g0 = gpu_used()
t0 = time.time()
p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", bufsize=1)


def read_until(done):
    for line in p.stdout:
        if line.startswith("{"):
            j = json.loads(line)
            if done(j):
                return j
    raise SystemExit("the brain ended")


ready = read_until(lambda j: j.get("event") in ("ready", "error"))
start_s = time.time() - t0
proc = psutil.Process(p.pid)
time.sleep(2)
g1 = gpu_used()
mi = proc.memory_info()
print(f"{mode} {lang}: ready in {start_s:.1f} s; RAM working set {mi.rss / 2**30:.2f} GB, private {mi.private / 2**30:.2f} GB; "
      f"GPU memory +{g1 - g0} MiB")

wavs = sorted(glob.glob(os.path.join(HERE, "stt", "wav_" + ("ru" if lang == "ru" else "clean"), "*.wav")))[::29][:n]
qid = 0
rows = []
for i, w in enumerate(wavs):
    qid += 1
    t = time.perf_counter()
    p.stdin.write(json.dumps({"cmd": "wav", "id": qid, "path": w, "world": mt.world(100 + 10 * i, {})}, ensure_ascii=False) + "\n")
    p.stdin.flush()
    r = read_until(lambda j: j.get("id") == qid)
    reply_ms = (time.perf_counter() - t) * 1000
    turn = (r.get("turns") or [r])[0]
    say = turn.get("say") or r.get("say") or ""
    voice_ms = None
    if say:
        qid += 1
        tv = time.perf_counter()
        p.stdin.write(json.dumps({"cmd": "say", "id": qid, "text": say, "stream": True}, ensure_ascii=False) + "\n")
        p.stdin.flush()
        read_until(lambda j: j.get("id") == qid and j.get("event") in ("speech", "speech_part", "error", "hushed"))
        voice_ms = (time.perf_counter() - tv) * 1000
    rows.append((reply_ms, voice_ms))
    time.sleep(0.6)
mi = proc.memory_info()
print(f"{mode} {lang}: after {len(rows)} lines RAM working set {mi.rss / 2**30:.2f} GB, private {mi.private / 2**30:.2f} GB; "
      f"GPU memory +{gpu_used() - g0} MiB")
p.stdin.write('{"cmd":"quit"}\n'); p.stdin.flush()
try:
    p.wait(timeout=30)
except subprocess.TimeoutExpired:
    p.kill()


def pct(a, q):
    a = sorted(a); k = (len(a) - 1) * q / 100; f = int(k); c = min(f + 1, len(a) - 1)
    return a[f] + (a[c] - a[f]) * (k - f)


rep = [r[0] for r in rows]
tot = [r[0] + (r[1] or 0) for r in rows]
print(f"{mode} {lang}: clip -> reply  P50 {pct(rep, 50):.0f}  P90 {pct(rep, 90):.0f}  P95 {pct(rep, 95):.0f}  max {max(rep):.0f} ms")
print(f"{mode} {lang}: clip -> first voice audio  P50 {pct(tot, 50):.0f}  P90 {pct(tot, 90):.0f}  P95 {pct(tot, 95):.0f}  max {max(tot):.0f} ms")
