"""Round talk-1 (2026-11-11): Qwen3-1.7B taught to talk in a role (cpp/coop_intent talker.h; TALK.md says what a row is).

The prompt is built exactly as the brain builds it in C++ (coop_cli's Chat::TalkSystem and talk_text.cpp's TalkPrompt): the
role's text with its name, "Your name is ...", for the bot the player's name, "You now: <scene>.", "The player is looking at
the <thing>.", the habit of «брат», then "Answer in <language> only, in one or two short sentences."; the earlier exchanges;
the line; the assistant turn opened with an empty think block. The loss is on the answer's tokens and its end-of-turn token.

    python talk_train.py check                 rows: counts per file, role, language, history; problems; the prompts' lengths
    python talk_train.py train [SEED]          QLoRA (r16 on every projection, 2e-4, 3 epochs) -> stt/models_out/talk/talk1_s<SEED>/adapter
    python talk_train.py gguf [SEED]           merged into the bf16 base -> GGUF f16 -> Q4_K_M -> models/coop-talk-v2/cpp/talk.gguf
                                               (+ talk_config.json and roles/ from coop-talk-v1)

The rows are rows/*.jsonl; test/ is the held-out set (talk_eval.py) and is never read here.
"""
import glob, hashlib, json, math, os, random, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STT = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
CACHE = os.path.join(STT, "models", "hf")
BASE = os.environ.get("TALK_BASE", "Qwen/Qwen3-1.7B")   # TALK_BASE=Qwen/Qwen3-4B: the same rows on the bigger model
ROLES_DIR = os.path.join(REPO, "models", "coop-talk-v1", "cpp", "roles")
OUT = os.path.join(STT, "models_out", "talk")
V2 = os.environ.get("TALK_MODEL_DIR", os.path.join(REPO, "models", "coop-talk-v2", "cpp"))   # where gguf writes the model
LL = os.path.join(STT, "models", "llama.cpp")
BUILD = "b11429"
LANGS = {"ru": "Russian", "en": "English", "es": "Spanish"}
BRO = {"ru": "брат", "en": "bro", "es": "hermano"}
HP = dict(r=16, alpha=32, dropout=0.05, lr=2e-4, epochs=int(os.environ.get("TALK_EPOCHS", "3")), batch=16, warmup=0.06, weight_decay=0.01)
TAG = os.environ.get("TALK_TAG", "talk1")   # the run's name: stt/models_out/talk/<TAG>_s<SEED>
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def role_text_file(name):
    """talk_config.json's role file as coop_cli's RoleText reads it: no BOM, no CR, no blank ends."""
    with open(os.path.join(ROLES_DIR, name + ".txt"), encoding="utf-8-sig") as f:
        return f.read().replace("\r", "").strip(" \t\n")


ROLE_TEXTS = {"bot": role_text_file("bot"), "seller": role_text_file("seller")}


def talk_system(row):
    """Chat::TalkSystem: the role's character, what the speaker is called, the bot's moment, the language."""
    role = row["role"]
    text = (row.get("role_text") or "").replace("\r", "").strip(" \t\n") if role == "other" else ROLE_TEXTS[role]
    name = row.get("name") or ""
    s = text.replace("{name}", name) if name else text
    s += "\n"
    if name:
        s += "\nYour name is " + name + "."
    if role == "bot":
        if row.get("player"):
            s += "\nThe player's name is " + row["player"] + "."
        if row.get("scene"):
            s += "\nYou now: " + row["scene"] + "."
        if row.get("looking_at"):
            s += "\nThe player is looking at the " + row["looking_at"] + "."
        if row.get("bro"):
            s += '\nYou call the player "' + BRO[row["lang"]] + '" now and then.'
    s += "\nAnswer in " + LANGS[row["lang"]] + " only, in one or two short sentences."
    return s


def talk_prompt(system, before, line):
    """talk_text.cpp's TalkPrompt."""
    out = "<|im_start|>system\n" + system + "<|im_end|>\n"
    for u, a in before:
        out += "<|im_start|>user\n" + u + "<|im_end|>\n<|im_start|>assistant\n" + a + "<|im_end|>\n"
    out += "<|im_start|>user\n" + line + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    return out


def read_rows(pattern):
    rows, problems = [], []
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8-sig") as f:
            for n, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    r = json.loads(raw)
                except json.JSONDecodeError as e:
                    problems.append(f"{os.path.basename(path)}:{n}: not JSON ({e})")
                    continue
                r["_file"] = os.path.basename(path)
                why = row_problem(r)
                if why:
                    problems.append(f"{r['_file']}:{n}: {why}")
                    continue
                rows.append(r)
    return rows, problems


def row_problem(r):
    if r.get("role") not in ("bot", "seller", "other"):
        return "role"
    if r.get("lang") not in LANGS:
        return "lang"
    if not isinstance(r.get("line"), str) or not r["line"].strip() or not isinstance(r.get("answer"), str) or not r["answer"].strip():
        return "line or answer"
    if r["role"] == "other" and not (r.get("role_text") or "").strip():
        return "other without role_text"
    b = r.get("before") or []
    if not isinstance(b, list) or any(not (isinstance(x, list) and len(x) == 2 and all(isinstance(y, str) for y in x)) for x in b):
        return "before"
    if len(b) > 3:
        return "before longer than 3"
    return None


def check():
    rows, problems = read_rows(os.path.join(HERE, "rows", "*.jsonl"))
    from collections import Counter
    print(f"{len(rows)} rows, {len(problems)} refused")
    for p in problems[:30]:
        print("  refused", p)
    for key in ("_file", "role", "lang"):
        print(key, dict(Counter(r[key] for r in rows)))
    print("before", dict(Counter(len(r.get("before") or []) for r in rows)), "scene", sum(1 for r in rows if r.get("scene")),
          "looking_at", sum(1 for r in rows if r.get("looking_at")), "bro", sum(1 for r in rows if r.get("bro")),
          "player", sum(1 for r in rows if r.get("player")))
    dup = Counter((r["role"], r["lang"], r["line"].strip().lower(), json.dumps(r.get("before") or [], ensure_ascii=False)) for r in rows)
    print("same line in the same talk more than once:", sum(c - 1 for c in dup.values() if c > 1))
    words = [len(r["answer"].split()) for r in rows]
    print(f"answer words: median {sorted(words)[len(words) // 2]}, max {max(words)}, over 30: {sum(1 for w in words if w > 30)}")
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(BASE, cache_dir=CACHE)
    lens = [len(tok(talk_prompt(talk_system(r), r.get("before") or [], r["line"]), add_special_tokens=False)["input_ids"]) for r in rows]
    print(f"prompt tokens: median {sorted(lens)[len(lens) // 2]}, max {max(lens)}")
    return rows


def free(device="cuda"):
    import gc, torch
    gc.collect()
    torch.cuda.empty_cache()


def train(seed):
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, get_linear_schedule_with_warmup
    rows, problems = read_rows(os.path.join(HERE, "rows", "*.jsonl"))
    print(f"{len(rows)} rows ({len(problems)} refused)", flush=True)
    random.seed(seed)
    torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(BASE, cache_dir=CACHE)
    end = tok.convert_tokens_to_ids("<|im_end|>")
    pad = tok.pad_token_id if tok.pad_token_id is not None else end
    data = []
    for r in rows:
        p = tok(talk_prompt(talk_system(r), r.get("before") or [], r["line"]), add_special_tokens=False)["input_ids"]
        a = tok(r["answer"].strip(), add_special_tokens=False)["input_ids"] + [end]
        data.append((p, a))
    q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(BASE, cache_dir=CACHE, quantization_config=q, dtype=torch.bfloat16, device_map={"": 0})
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(model, LoraConfig(r=HP["r"], lora_alpha=HP["alpha"], lora_dropout=HP["dropout"], target_modules=TARGETS, task_type="CAUSAL_LM"))
    steps = HP["epochs"] * math.ceil(len(data) / HP["batch"])
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=HP["lr"], weight_decay=HP["weight_decay"])
    sched = get_linear_schedule_with_warmup(opt, int(HP["warmup"] * steps), steps)
    lm = model.get_base_model()
    model.train()
    order = list(range(len(data)))
    step, t0, run = 0, time.time(), []
    for epoch in range(HP["epochs"]):
        random.shuffle(order)
        for b in range(0, len(order), HP["batch"]):
            idx = order[b:b + HP["batch"]]
            seqs = [data[j][0] + data[j][1] for j in idx]
            n = max(map(len, seqs))
            x = torch.full((len(seqs), n), pad, dtype=torch.long)
            m = torch.zeros((len(seqs), n), dtype=torch.long)
            y = torch.full((len(seqs), n), -100, dtype=torch.long)
            for i, j in enumerate(idx):
                p, a = data[j]
                x[i, :len(p) + len(a)] = torch.tensor(p + a)
                m[i, :len(p) + len(a)] = 1
                y[i, len(p):len(p) + len(a)] = torch.tensor(a)
            x, m, y = x.cuda(), m.cuda(), y.cuda()
            # the loss from the answer's positions alone (qlora_v54.train with checkpoint: no projection of every position)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                h = lm.model(input_ids=x, attention_mask=m, use_cache=False).last_hidden_state
                keep = y[:, 1:] != -100
                logits = lm.lm_head(h[:, :-1][keep])
            loss = torch.nn.functional.cross_entropy(logits.float(), y[:, 1:][keep])
            loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            step += 1
            run.append(loss.item())
            if step % 25 == 0 or step == steps:
                print(f"epoch {epoch + 1} step {step}/{steps} loss {sum(run) / len(run):.4f} ({time.time() - t0:.0f} s)", flush=True)
                run = []
    out = os.path.join(OUT, f"{TAG}_s{seed}", "adapter")
    os.makedirs(out, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    digest = hashlib.sha1("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows).encode("utf-8")).hexdigest()[:12]
    with open(os.path.join(OUT, f"{TAG}_s{seed}", "train.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": len(rows), "rows_sha1": digest, "hp": HP, "seed": seed, "steps": steps, "seconds": round(time.time() - t0)}, f, indent=1)
    print(f"adapter -> {out} ({time.time() - t0:.0f} s)", flush=True)


def gguf(seed):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    adapter = os.path.join(OUT, f"{TAG}_s{seed}", "adapter")
    merged = os.path.join(OUT, f"{TAG}_s{seed}", "merged")
    f16 = os.path.join(OUT, f"{TAG}_s{seed}", "talk-f16.gguf")
    base = AutoModelForCausalLM.from_pretrained(BASE, cache_dir=CACHE, dtype=torch.bfloat16)
    PeftModel.from_pretrained(base, adapter).merge_and_unload().save_pretrained(merged, safe_serialization=True)
    AutoTokenizer.from_pretrained(BASE, cache_dir=CACHE).save_pretrained(merged)
    src = os.path.join(LL, "src", f"llama.cpp-{BUILD}")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([src, os.path.join(src, "gguf-py")]))
    subprocess.run([sys.executable, os.path.join(src, "convert_hf_to_gguf.py"), merged, "--outfile", f16, "--outtype", "f16"], check=True, env=env)
    os.makedirs(os.path.join(V2, "roles"), exist_ok=True)
    subprocess.run([os.path.join(LL, f"{BUILD}-cpu", "llama-quantize.exe"), f16, os.path.join(V2, "talk.gguf"), "Q4_K_M", "8"], check=True)
    shutil.rmtree(merged)
    os.remove(f16)
    v1 = os.path.join(REPO, "models", "coop-talk-v1", "cpp")
    with open(os.path.join(v1, "talk_config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["model_from"] = (f"{BASE} (Apache-2.0) + {TAG} seed {seed} ({HP['epochs']} epochs, QLoRA r16 on every projection, scripts/coop/stt/talk/talk_train.py), "
                         f"merged, llama.cpp {BUILD} Q4_K_M")
    with open(os.path.join(V2, "talk_config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
        f.write("\n")
    for p in glob.glob(os.path.join(v1, "roles", "*.txt")):
        shutil.copy2(p, os.path.join(V2, "roles"))
    print(f"-> {V2} ({os.path.getsize(os.path.join(V2, 'talk.gguf')) / 2 ** 20:.0f} MB)", flush=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "check"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    {"check": lambda: check(), "train": lambda: train(seed), "gguf": lambda: gguf(seed)}[what]()
