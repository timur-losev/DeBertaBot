"""Does the rewriter read a line differently when it is shown five earlier lines instead of the none, one or two it was
trained with (chain_config.json "memory_lines": five since 2026-10-14, the owner's choice)? The engine's own test lines
(models/coop-chain-v54/cpp/chain_tests.jsonl: held-out singles, development chains, the teacher's context items; none
from an unread set), each asked twice on llama.cpp's server, CPU, one after the other:
  as it is   0, 1 or 2 earlier lines: the file's answer, but for what the order of the prompts changes (3 of 160)
  five       older lines put in front until there are five: what the longer memory shows the decoder in a game
The older lines are other test lines that stand alone and were written back as they are; one draw (seed 5405). Nothing
is labelled: the two answers are compared with each other. Writes memory_lines_probe.json.

    python memory_lines_probe.py        about 6 minutes on four threads"""
import io, json, os, random, subprocess, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CHAIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models", "coop-chain-v54", "cpp"))
SERVER = os.path.join(HERE, "models", "llama.cpp", "b11429-cpu", "llama-server.exe")
OUT = os.path.join(HERE, "memory_lines_probe.json")
PORT = 8731
cfg = json.load(io.open(os.path.join(CHAIN, "chain_config.json"), encoding="utf-8"))
rows = [json.loads(l) for l in io.open(os.path.join(CHAIN, "chain_tests.jsonl"), encoding="utf-8") if l.strip()]


def turn(before, bot, line):                      # rewriter_text.cpp RewriterTurn
    return "".join(f"before: {b}\n" for b in before) + (f"bot: {bot}\n" if bot else "") + f"now: {line}"


def prompt(t):                                    # rewriter_text.cpp RewriterPrompt
    return f"<|im_start|>system\n{cfg['system']}<|im_end|>\n<|im_start|>user\n{t}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def pieces(a):
    return [p.strip() for p in a.split("\n") if p.strip()]


def call(path, body=None, timeout=600):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=None if body is None else json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))


def ask(t):
    a = call("/completion", {"prompt": prompt(t), "n_predict": cfg["max_new"], "temperature": 0, "top_k": 1, "cache_prompt": True,
                             "stop": ["<|im_end|>"], "stream": False})
    return a["content"], a.get("tokens_evaluated", 0)


# older orders: lines of the file that stand alone, were answered with themselves, and are one order
pool = [r["line"] for r in rows if not r["before"] and not r["bot"] and pieces(r["answer"]) == [r["line"].strip()]]
rng = random.Random(5405)
log = io.open(os.devnull, "w", encoding="utf-8")
proc = subprocess.Popen([SERVER, "-m", os.path.join(CHAIN, "decoder.gguf"), "--host", "127.0.0.1", "--port", str(PORT), "-c", str(cfg["context"]),
                         "--parallel", "1", "-ngl", "0", "-t", "4"], stdout=log, stderr=subprocess.STDOUT)
out = []
try:
    t0 = time.time()
    while True:
        try:
            if call("/health", timeout=5).get("status") == "ok":
                break
        except Exception:  # noqa: BLE001  (not up yet)
            if proc.poll() is not None or time.time() - t0 > 180:
                raise SystemExit("llama-server did not start")
            time.sleep(1)
    for i, r in enumerate(rows):
        older = [x for x in rng.sample(pool, 8) if x != r["line"] and x not in r["before"]][:5 - len(r["before"])]
        base, n0 = ask(turn(r["before"], r["bot"], r["line"]))
        five, n5 = ask(turn(older + r["before"], r["bot"], r["line"]))
        out.append({"i": i, "before": r["before"], "bot": r["bot"], "line": r["line"], "route": r.get("route"), "older": older,
                    "file": r["answer"], "base": base, "five": five, "tokens_base": n0, "tokens_five": n5})
        if i % 20 == 19:
            print(f"{i + 1}/{len(rows)}  {time.time() - t0:.0f} s", flush=True)
finally:
    proc.terminate()
    proc.wait(timeout=60)
    log.close()
json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def plain(a):                                     # capitals and punctuation aside: what the classifier is given
    return [" ".join("".join(c for c in p.lower() if c not in ".!?,").split()) for p in pieces(a)]


same_file = sum(pieces(o["base"]) == pieces(o["file"]) for o in out)
diff = [o for o in out if plain(o["five"]) != plain(o["base"])]
sent = [o for o in out if (o["route"] or 0) >= cfg.get("cut", 0.5)]
own = [o for o in out if o["before"] or o["bot"]]
print(f"{len(out)} lines; as it is equals the file's answer on {same_file}; longest prompt {max(o['tokens_five'] for o in out)} tokens")
print(f"five earlier lines change the order lines (capitals and punctuation aside) on {len(diff)}: {sum(o in diff for o in sent)} of the {len(sent)} "
      f"the router sends on, {sum(o in diff for o in own)} of the {len(own)} with earlier lines of their own")
print(f"lines of several orders among those the router sends on: {sum(len(pieces(o['base'])) > 1 for o in sent)} as they are, "
      f"{sum(len(pieces(o['five'])) > 1 for o in sent)} with five")
for o in diff:
    print(f"  {o['line']}\n      as it is  {pieces(o['base'])}\n      with five {pieces(o['five'])}")
