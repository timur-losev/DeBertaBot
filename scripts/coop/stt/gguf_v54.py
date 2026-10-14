"""The decoder as a game would run it: merged into its base, converted to GGUF, quantized to 4 bits, served by llama.cpp.

The adapters of chains2_v54.py are trained on a base PyTorch holds in 4 bits (NF4). A game ships one file in llama.cpp's
format with another 4-bit scheme (Q4_K_M), so the weights the adapter was fitted to are not the weights it runs on.
Two questions: do the answers change, and what does a line cost in time and memory, on the GPU (the Vulkan build: any
vendor's card) and on the CPU alone.

    python gguf_v54.py make VARIANT SEED            merge, convert, quantize -> models/gguf/<VARIANT>_s<SEED>-Q4_K_M.gguf
    python gguf_v54.py bench VARIANT SEED BACKEND [N]   BACKEND: vulkan | cpu4 | cpu8 (threads) -> gguf54_<VARIANT>_s<SEED>_<BACKEND>.json
                                                    (N lines of each set; by default all on the GPU and 50 on the CPU)
    python gguf_v54.py score                        time and memory, and the answers against the PyTorch model's and the truth

Needs llama.cpp next to the downloaded models: models/llama.cpp/<BUILD>-vulkan and <BUILD>-cpu (the release's Windows
builds, unpacked) and models/llama.cpp/src/llama.cpp-<BUILD> (its source, for convert_hf_to_gguf.py). The server runs
on 127.0.0.1 and is stopped at the end. One slot, the prompt cache on: the system turn is computed once, a line costs
its own tokens and its answer's, as qlora_v54.py timing does in PyTorch.
"""
import io, json, os, shutil, subprocess, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chains2_v54 as C2
from chains2_v54 import B, C, Q

BUILD = "b11429"
LL = os.path.join(HERE, "models", "llama.cpp")
SRC = os.path.join(LL, "src", f"llama.cpp-{BUILD}")
GG = os.path.join(HERE, "models", "gguf")
BACKENDS = {"vulkan": ("vulkan", ["-ngl", "99"]), "cpu4": ("cpu", ["-ngl", "0", "-t", "4"]), "cpu8": ("cpu", ["-ngl", "0", "-t", "8"])}
PORT = 8719
N_CPU = 50            # lines per set on the CPU, where a line takes seconds


def gguf_path(variant, seed):
    return os.path.join(GG, f"{variant}_s{seed}-Q4_K_M.gguf")


def make(variant, seed):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t0 = time.time()
    os.makedirs(GG, exist_ok=True)
    stem = os.path.join(GG, f"{variant}_s{seed}")
    merged, f16 = stem + "-merged", stem + "-f16.gguf"
    base = AutoModelForCausalLM.from_pretrained(Q.MODELS[C2.LLM.get(variant, C.NAME)], cache_dir=Q.CACHE, dtype=torch.bfloat16)
    PeftModel.from_pretrained(base, C2.adapter_dir(variant, seed)).merge_and_unload().save_pretrained(merged, safe_serialization=True)
    AutoTokenizer.from_pretrained(Q.MODELS[C2.LLM.get(variant, C.NAME)], cache_dir=Q.CACHE).save_pretrained(merged)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([SRC, os.path.join(SRC, "gguf-py")]))
    subprocess.run([sys.executable, os.path.join(SRC, "convert_hf_to_gguf.py"), merged, "--outfile", f16, "--outtype", "f16"], check=True, env=env)
    subprocess.run([os.path.join(LL, f"{BUILD}-cpu", "llama-quantize.exe"), f16, gguf_path(variant, seed), "Q4_K_M"], check=True)
    shutil.rmtree(merged)
    os.remove(f16)
    print(f"{variant} seed {seed}: {os.path.getsize(gguf_path(variant, seed)) / 2 ** 20:.0f} MB, {time.time() - t0:.0f}s -> {gguf_path(variant, seed)}", flush=True)


def call(path, body=None, timeout=300):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def gpu_used_mb():
    """Video memory in use on the card, all processes (nvidia-smi does not say it per process on Windows): the server's
    share is the difference between before it starts and after it has answered, on a card nothing else is using."""
    try:
        return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=60).stdout.split()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def bench(variant, seed, backend, limit=None):
    import psutil
    from transformers import AutoTokenizer
    kind = C2.KIND[variant]
    build, extra = BACKENDS[backend]
    turns = Q.Turns(AutoTokenizer.from_pretrained(Q.MODELS[C2.LLM.get(variant, C.NAME)], cache_dir=Q.CACHE), C2.SYSTEM[kind])
    ts = C2.tests()
    sets = {"blind2": ts["blind2"], "ctx": ts["ctx"] if kind == "pieces" else [], "singles": [t for t in ts["singles"] if t["id"].startswith("typed|")]}
    if limit or build == "cpu":
        sets = {k: v[:limit or N_CPU] for k, v in sets.items()}
    log = io.open(os.path.join(HERE, f"gguf54_{variant}_s{seed}_{backend}.server.log"), "w", encoding="utf-8")
    gpu0 = gpu_used_mb()
    proc = subprocess.Popen([os.path.join(LL, f"{BUILD}-{build}", "llama-server.exe"), "-m", gguf_path(variant, seed), "--host", "127.0.0.1",
                             "--port", str(PORT), "-c", "2048", "--parallel", "1", *extra], stdout=log, stderr=subprocess.STDOUT)
    try:
        t0 = time.time()
        while True:
            try:
                if call("/health", timeout=5).get("status") == "ok":
                    break
            except Exception:  # noqa: BLE001  (not up yet)
                if proc.poll() is not None or time.time() - t0 > 180:
                    raise SystemExit(f"llama-server did not start: see {log.name}")
                time.sleep(1)
        load_s = time.time() - t0

        def ask(t):
            line = t["text"] if kind == "names" else C2.turn(t.get("before", []), t.get("bot"), t["text"])
            t1 = time.perf_counter()
            r = call("/completion", {"prompt": turns.text(line), "n_predict": C2.MAX_NEW[kind], "temperature": 0, "top_k": 1, "cache_prompt": True,
                                     "stop": ["<|im_end|>"], "stream": False})
            tm = r.get("timings", {})
            return {"answer": r["content"].strip(), "ms": round(1000 * (time.perf_counter() - t1), 1), "prompt_n": tm.get("prompt_n"),
                    "prompt_ms": tm.get("prompt_ms"), "predicted_n": tm.get("predicted_n"), "predicted_ms": tm.get("predicted_ms")}

        for t in sets["blind2"][:3]:                      # the first lines warm the model up and are asked again below
            ask(t)
        rows = {name: {t["id"]: ask(t) for t in ts_} for name, ts_ in sets.items() if ts_}
        p = psutil.Process(proc.pid)
        gpu1 = gpu_used_mb()
        out = {"variant": variant, "seed": seed, "backend": backend, "build": BUILD, "gguf_mb": round(os.path.getsize(gguf_path(variant, seed)) / 2 ** 20),
               "load_s": round(load_s, 1), "rss_mb": round(p.memory_info().rss / 2 ** 20),
               "gpu_mb": gpu1 - gpu0 if build != "cpu" and None not in (gpu0, gpu1) else 0,
               "cpu": os.environ.get("PROCESSOR_IDENTIFIER", ""), "rows": rows}
    finally:
        proc.terminate()
        log.close()
    json.dump(out, io.open(os.path.join(HERE, f"gguf54_{variant}_s{seed}_{backend}.json"), "w", encoding="utf-8"), indent=1)
    n = sum(len(v) for v in rows.values())
    print(f"{variant} seed {seed} on {backend}: {n} lines, {sum(r['ms'] for v in rows.values() for r in v.values()) / n:.0f} ms a line, "
          f"{out['rss_mb']} MB of memory, {out['gpu_mb']} MB of video memory", flush=True)


def score():
    ts = C2.tests()
    files = sorted(f for f in os.listdir(HERE) if f.startswith("gguf54_") and f.endswith(".json"))
    runs = [C2.jload(HERE, f) for f in files]
    # every piece the GGUF models wrote, read by the v54 ensemble
    texts = sorted({B.norm(p) for r in runs if C2.KIND[r["variant"]] == "pieces" for name in ("blind2", "ctx") for a in r["rows"].get(name, {}).values() for p in C2.split(a["answer"])}
                   | {B.norm(p) for r in runs if C2.KIND[r["variant"]] == "pieces" for name in ("blind2", "ctx") for a in C2.jload(C2.out_path(r["variant"], r["seed"]))["pred"][name].values() for p in C2.split(a)})
    picks = {}
    if texts:
        got, _ = C.bot_picks([{"id": str(n), "text": t} for n, t in enumerate(texts)])
        picks = {t: [got[str(n)][0]] for n, t in enumerate(texts)}

    def right(kind, name, t, answer):
        if kind == "names":
            return C.parse(answer) == t["orders"]
        pieces = C2.split(answer)
        intents = C2.orders_of(pieces, picks) == t["orders"]
        if name != "ctx":
            return intents
        return intents and (t["places"] is None or [C2.place(p) for p in pieces] == [tuple(x) if x is not None else None for x in t["places"]])

    for r in runs:
        kind = C2.KIND[r["variant"]]
        torch_pred = C2.jload(C2.out_path(r["variant"], r["seed"]))["pred"]
        print(f"\n{r['variant']} seed {r['seed']}, Q4_K_M ({r['gguf_mb']} MB), llama.cpp {r['build']} {r['backend']}: loaded in {r['load_s']} s, "
              f"{r['rss_mb']} MB of memory" + (f", {r['gpu_mb']} MB of video memory" if r["gpu_mb"] else "") + f"; {r['cpu']}")
        print(f"  {'lines':34s} {'n':>4s} {'ms a line':>10s} {'median':>7s} {'p95':>7s} {'tokens in':>10s} {'out':>5s} {'out per s':>10s} {'same as PyTorch':>16s} {'right':>7s} {'(PyTorch)':>10s}")
        for name, label in (("singles", "old single lines, typed"), ("blind2", "this round's blind lines"), ("ctx", "lines with a context")):
            rows = r["rows"].get(name)
            if not rows:
                continue
            ms = sorted(a["ms"] for a in rows.values())
            n_in = sum(a["prompt_n"] or 0 for a in rows.values()) / len(rows)
            n_out = sum(a["predicted_n"] or 0 for a in rows.values()) / len(rows)
            per_s = 1000 * sum(a["predicted_n"] or 0 for a in rows.values()) / max(sum(a["predicted_ms"] or 0 for a in rows.values()), 1e-9)
            norm = lambda s: [B.norm(p) for p in C2.split(s)] if kind == "pieces" else C.parse(s)  # noqa: E731
            # a set PyTorch was not asked about (a model for the game was trained on the old single lines): timing only
            same = f"{100 * sum(norm(a['answer']) == norm(torch_pred[name][k]) for k, a in rows.items()) / len(rows):15.1f}%" if name in torch_pred else f"{'':16s}"
            truth = {t["id"]: t for t in ts[name] if t.get("orders")}
            acc = ""
            if name != "singles" and truth:
                ids = [k for k in rows if k in truth]
                acc = (f"{100 * sum(right(kind, name, truth[k], rows[k]['answer']) for k in ids) / len(ids):7.1f} "
                       f"{100 * sum(right(kind, name, truth[k], torch_pred[name][k]) for k in ids) / len(ids):10.1f}")
            print(f"  {label:34s} {len(rows):4d} {sum(ms) / len(ms):10.0f} {ms[len(ms) // 2]:7.0f} {ms[int(0.95 * (len(ms) - 1))]:7.0f} {n_in:10.1f} {n_out:5.1f} {per_s:10.0f} {same} {acc}")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "make":
        make(sys.argv[2], int(sys.argv[3]))
    elif mode == "bench":
        bench(sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else None)
    elif mode == "score":
        score()
    else:
        sys.exit(__doc__)
