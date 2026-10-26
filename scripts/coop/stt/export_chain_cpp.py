"""What the C++ engine (cpp/coop_intent: rewriter.h, coop_cli --chain) needs for lines with several orders or with a
context, and the data it is checked against. Writes into models/coop-chain-v54/cpp/ (for another variant than the
game's: models/coop-chain-<VARIANT>-s<SEED>-v54/cpp/):

  chain_config.json   the router's file and its cut, the decoder's file, its system turn and its longest answer, how many
                      earlier lines the bot keeps and for how long
  router.onnx         the two-class router (router_v54.py train final), exported as a bot's member is (export_cpp.py);
                      it reads the bot's own token ids: deberta-v3-small and -base share one vocabulary (checked here)
  decoder.gguf        the rewriter (gguf_v54.py make): a hard link to models/gguf/<VARIANT>_s<SEED>-Q4_K_M.gguf
  chain_tests.jsonl   per line: the earlier lines, the bot's line, the scene (decoder v65 on) and the line; the token ids and the router's
                      probability from PyTorch; the decoder's answer from llama.cpp's own server on the CPU with the
                      prompt cache on, in file order (the C++ check runs the decoder on the CPU too: a GPU may round
                      another way)

    python export_chain_cpp.py [VARIANT SEED] [--no-router]     default: pieces3_final 0
"""
import io, json, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import torch
import gguf_v54 as G
from gguf_v54 import B, C, C2, Q

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
VARIANT, SEED = (ARGS[0], int(ARGS[1])) if ARGS else ("pieces3_final", 0)
WITH_ROUTER = "--no-router" not in sys.argv
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "models"))
OUT = os.path.join(MODELS, "coop-chain-v54" if VARIANT == "pieces3_final" else f"coop-chain-{VARIANT}-s{SEED}-v54", "cpp")
ROUTER = os.path.join(MODELS, "coop-router-deberta-v3-small-v54")
BOT = os.path.join(C.BOT, "seed0")          # a member of the bot: its tokenizer is the engine's
# The earlier lines the decoder is shown, and how long they count. Five is the owner's choice (2026-10-14); the decoder
# was trained with none, one or two (spec_context.json), so the third to the fifth are a prompt it has not seen
MEMORY_LINES, MEMORY_SECONDS = 5, 30.0
N_EACH = 40


def test_rows():
    """Lines of three kinds, none of them from a set that is still unread: held-out single lines, the development
    chains, and the teacher's context items (with their earlier lines and the bot's line)."""
    ts = C2.tests()
    rows = [{"before": [], "bot": None, "line": t["text"]} for t in ts["singles"] if t["id"].startswith("typed|")][:N_EACH]
    rows += [{"before": [], "bot": None, "line": t["text"]} for t in ts["blind"]][:N_EACH]
    rows += [{"before": x["before"], "bot": x["bot"], "line": x["line"]} for x in C2.context_items()][:N_EACH]
    # the bot's text for a line it heard: lowercased, the final .!? stripped
    rows += [{"before": [B.norm(b) for b in r["before"]], "bot": r["bot"], "line": B.norm(r["line"])} for r in rows[N_EACH:N_EACH + 20] + rows[-20:]]
    return rows


def main():
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    os.makedirs(OUT, exist_ok=True)
    kind = C2.KIND[VARIANT]
    assert kind == "pieces", "the engine's decoder is a rewriter"
    src = G.gguf_path(VARIANT, SEED)
    dst = os.path.join(OUT, "decoder.gguf")
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)                   # the same file under a second name: no second gigabyte
    except OSError:
        shutil.copyfile(src, dst)
    rows = test_rows()
    cfg = {"decoder": "decoder.gguf", "decoder_from": f"{Q.MODELS[C2.LLM.get(VARIANT, C.NAME)]} + {VARIANT} seed {SEED}, Q4_K_M, llama.cpp {G.BUILD}",
           "system": C2.SYSTEM[kind], "max_new": C2.MAX_NEW[kind], "context": 1024,
           "memory_lines": MEMORY_LINES, "memory_seconds": MEMORY_SECONDS}

    # ---- the router: ONNX, and its probability for every test line
    tok = AutoTokenizer.from_pretrained(BOT)
    ids = [tok([r["line"]], truncation=True, max_length=64)["input_ids"][0] for r in rows]
    for r, x in zip(rows, ids):
        r["ids"] = x
    if WITH_ROUTER:
        rcfg = json.load(io.open(os.path.join(ROUTER, "router_config.json"), encoding="utf-8"))
        rtok = AutoTokenizer.from_pretrained(ROUTER)
        assert all(rtok([r["line"]], truncation=True, max_length=64)["input_ids"][0] == r["ids"] for r in rows), "the router's tokenizer is not the bot's"
        model = AutoModelForSequenceClassification.from_pretrained(ROUTER, dtype=torch.float32).eval()

        class Wrap(torch.nn.Module):
            def __init__(self, m):
                super().__init__()
                self.m = m

            def forward(self, input_ids, attention_mask):
                return self.m(input_ids=input_ids, attention_mask=attention_mask).logits

        x = tok(["breach on my go", "come here"], padding=True, return_tensors="pt")
        torch.onnx.export(Wrap(model), (x["input_ids"], x["attention_mask"]), os.path.join(OUT, "router.onnx"),
                          input_names=["input_ids", "attention_mask"], output_names=["logits"],
                          dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}, "logits": {0: "batch"}},
                          opset_version=17, dynamo=False)
        model.eval()                        # export_cpp.py: the export leaves a fresh wrapper in training mode
        with torch.no_grad():
            for r in rows:
                logits = model(input_ids=torch.tensor([r["ids"]]), attention_mask=torch.ones(1, len(r["ids"]), dtype=torch.long)).logits[0]
                r["route"] = float(torch.softmax(logits.double(), -1)[1])
        cfg.update({"router": "router.onnx", "cut": rcfg["cut"], "router_from": f"{rcfg['base_model']}, {rcfg['rows']} rows, seed {rcfg['seed']}"})

    # ---- the decoder's answers from llama.cpp's server, CPU, one slot, the prompt cache on, in this order
    turns = Q.Turns(AutoTokenizer.from_pretrained(Q.MODELS[C2.LLM.get(VARIANT, C.NAME)], cache_dir=Q.CACHE), C2.SYSTEM[kind])
    log = io.open(os.path.join(OUT, "llama_server.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([os.path.join(G.LL, f"{G.BUILD}-cpu", "llama-server.exe"), "-m", dst, "--host", "127.0.0.1", "--port", str(G.PORT),
                             "-c", str(cfg["context"]), "--parallel", "1", "-ngl", "0", "-t", "4"], stdout=log, stderr=subprocess.STDOUT)
    try:
        t0 = time.time()
        while True:
            try:
                if G.call("/health", timeout=5).get("status") == "ok":
                    break
            except Exception:  # noqa: BLE001  (not up yet)
                if proc.poll() is not None or time.time() - t0 > 180:
                    raise SystemExit(f"llama-server did not start: see {log.name}")
                time.sleep(1)
        for r in rows:
            turn = C2.turn(r["before"], r["bot"], r["line"])
            if r.get("scene"):   # decoder v65 (chains9_v65.py): the game's scene line, right before "now:"
                head, sep, now = turn.rpartition("now: ")
                turn = f"{head}scene: {r['scene']}\n{sep}{now}"
            a = G.call("/completion", {"prompt": turns.text(turn), "n_predict": cfg["max_new"], "temperature": 0, "top_k": 1, "cache_prompt": True,
                                       "stop": ["<|im_end|>"], "stream": False})
            r["turn"], r["answer"] = turn, a["content"]
    finally:
        proc.terminate()
        proc.wait(timeout=60)               # Windows keeps the log open until the server is gone
        log.close()
    os.remove(log.name)
    json.dump(cfg, io.open(os.path.join(OUT, "chain_config.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUT, "chain_tests.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    sent = sum(r.get("route", 0) >= cfg.get("cut", 2) for r in rows)
    print(f"wrote {OUT}: decoder.gguf ({os.path.getsize(dst) / 2 ** 20:.0f} MB), " + (f"router.onnx (it sends {sent} of {len(rows)} test lines on), " if WITH_ROUTER else "no router, ")
          + f"{len(rows)} test lines, {sum(len(C2.split(r['answer'])) > 1 for r in rows)} answered with several orders")


if __name__ == "__main__":
    main()
