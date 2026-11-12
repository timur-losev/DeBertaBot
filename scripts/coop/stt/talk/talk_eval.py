"""Round talk-1: the held-out rows (test/*.jsonl, written blind by other writers) answered by the talking models, as the brain
asks them (talk_train.py's prompt, Qwen3's sampling with a fixed seed per row, 72 tokens at most, the answer made sayable as
talk_text.cpp's TalkAnswer does), then put side by side for a judge who does not know which model wrote which.

    python talk_eval.py answer TAG GGUF [cpu|gpu]   -> eval/answers_<TAG>.jsonl  (llama-server b11429)
    python talk_eval.py pairs TAG_A TAG_B           -> eval/pairs_<A>_<B>.jsonl (shuffled, "x"/"y") + eval/pairs_<A>_<B>.key.json
    python talk_eval.py score TAG_A TAG_B           eval/judged_<A>_<B>.jsonl (the judge's) + the key -> the tables
    python talk_eval.py auto TAG                    rules alone: the language, Chinese/Japanese/Korean, length, empty
"""
import glob, json, os, random, re, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from talk_train import LL, BUILD, talk_prompt, talk_system

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(HERE, "eval")
PORT = 8932
CJK = re.compile("[⺀-鿿가-힯豈-﫿＀-￯]")


def test_rows():
    rows = []
    for path in sorted(glob.glob(os.path.join(HERE, "test", "*.jsonl"))):
        with open(path, encoding="utf-8-sig") as f:
            rows += [json.loads(l) for l in f if l.strip()]
    return rows


def call(path, body=None, timeout=600):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def sayable(raw, cut_off):
    """talk_text.cpp's TalkAnswer, near enough for scoring: think blocks and markup out, one line, a leading "Name:" and quotes
    off, pictographs out, an answer cut by the limit up to its last finished sentence."""
    t = re.sub(r"<think>.*?(</think>|$)", "", raw, flags=re.S)
    t = re.sub(r"<\|.*?\|>", "", t)
    t = re.sub(r"[\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿︀-️‍⃣]", "", t)
    t = re.sub(r"[*_#`]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    m = re.match(r"^([A-ZА-ЯЁÀ-Þ][\w\-]*(?: [\w\-]+)?): (.+)$", t)
    if m and len(m.group(1)) <= 24:
        t = m.group(2)
    while len(t) >= 2 and t[0] in "\"«“„'" and t[-1] in "\"»”'":
        t = t[1:-1]
    if cut_off:
        ends = [i for i, c in enumerate(t) if c in ".!?…"]
        if ends:
            t = t[:ends[-1] + 1]
    t = t.lstrip(" -—").strip()
    return t


def in_language(text, lang):
    """talk_text.cpp's TalkInLanguage: also no word in two alphabets («колou»)."""
    cyr = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
    lat = sum(1 for c in text if c.isalpha() and c.isascii() or "À" <= c <= "ɏ")
    if CJK.search(text):
        return False
    for w in re.findall(r"[A-Za-zÀ-ɏЀ-ӿ]+", text):
        if re.search("[Ѐ-ӿ]", w) and re.search(r"[A-Za-zÀ-ɏ]", w):
            return False
    if cyr == 0 and lat == 0:
        return any(c.isdigit() for c in text)
    return cyr >= 2 and cyr >= lat if lang == "ru" else cyr == 0 and lat >= 2


def answer(tag, gguf, where="gpu"):
    os.makedirs(EVAL, exist_ok=True)
    rows = test_rows()
    log = open(os.path.join(EVAL, f"server_{tag}.log"), "w", encoding="utf-8")
    build = "vulkan" if where == "gpu" else "cpu"
    extra = ["-ngl", "99"] if where == "gpu" else ["-ngl", "0", "-t", "8"]
    proc = subprocess.Popen([os.path.join(LL, f"{BUILD}-{build}", "llama-server.exe"), "-m", gguf, "--host", "127.0.0.1", "--port", str(PORT),
                             "-c", "4096", "--parallel", "1", *extra], stdout=log, stderr=subprocess.STDOUT, creationflags=0x00004000)
    out = []
    try:
        t0 = time.time()
        while True:
            try:
                if call("/health", timeout=5).get("status") == "ok":
                    break
            except Exception:  # noqa: BLE001
                if proc.poll() is not None or time.time() - t0 > 300:
                    raise SystemExit("llama-server did not start")
                time.sleep(1)
        for i, r in enumerate(rows):
            prompt = talk_prompt(talk_system(r), r.get("before") or [], r["line"])
            t1 = time.perf_counter()
            res = call("/completion", {"prompt": prompt, "n_predict": 72, "temperature": float(os.environ.get("TALK_TEMP", "0.7")), "top_p": 0.8, "top_k": 20, "min_p": 0.0,
                                       "seed": 1000 + i, "cache_prompt": True, "stop": ["<|im_end|>"], "stream": False})
            raw = res.get("content", "")
            cut = bool(res.get("stop_type") == "limit" or res.get("truncated") or (res.get("tokens_predicted", 0) >= 72))
            out.append({"id": r["id"], "tag": tag, "raw": raw, "answer": sayable(raw, cut), "cut_off": cut,
                        "ms": round(1000 * (time.perf_counter() - t1)), "tokens": res.get("tokens_predicted")})
    finally:
        proc.terminate()
        proc.wait(30)
        log.close()
    with open(os.path.join(EVAL, f"answers_{tag}.jsonl"), "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"{tag}: {len(out)} answers, median {sorted(o['ms'] for o in out)[len(out) // 2]} ms -> {EVAL}")


def load_answers(tag):
    with open(os.path.join(EVAL, f"answers_{tag}.jsonl"), encoding="utf-8") as f:
        return {o["id"]: o for o in map(json.loads, f)}


def auto(tag):
    rows = {r["id"]: r for r in test_rows()}
    ans = load_answers(tag)
    from collections import Counter
    bad = Counter()
    for i, o in ans.items():
        r = rows[i]
        a = o["answer"]
        if not a:
            bad["empty"] += 1
        elif CJK.search(a):
            bad["cjk"] += 1
        elif not in_language(a, r["lang"]):
            bad["language"] += 1
        if len(a.split()) > 35:
            bad["long"] += 1
        if o["cut_off"]:
            bad["cut_off"] += 1
    print(tag, len(ans), dict(bad))


def pairs(a, b):
    rows = test_rows()
    A, B = load_answers(a), load_answers(b)
    rnd = random.Random(20261111)
    key, out = {}, []
    for r in rows:
        flip = rnd.random() < 0.5
        x, y = (B, A) if flip else (A, B)
        key[r["id"]] = {"x": b if flip else a, "y": a if flip else b}
        out.append({"id": r["id"], "role": r["role"], "lang": r["lang"], "name": r.get("name"), "scene": r.get("scene"),
                    "looking_at": r.get("looking_at"), "bro": r.get("bro"), "before": r.get("before") or [], "line": r["line"],
                    "reference": r["answer"], "x": x[r["id"]]["answer"], "y": y[r["id"]]["answer"]})
    rnd.shuffle(out)
    with open(os.path.join(EVAL, f"pairs_{a}_{b}.jsonl"), "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    with open(os.path.join(EVAL, f"pairs_{a}_{b}.key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f)
    print(f"{len(out)} pairs -> {EVAL}")


def score(a, b):
    with open(os.path.join(EVAL, f"pairs_{a}_{b}.key.json"), encoding="utf-8") as f:
        key = json.load(f)
    rows = {r["id"]: r for r in test_rows()}
    from collections import Counter, defaultdict
    per = defaultdict(Counter)
    with open(os.path.join(EVAL, f"judged_{a}_{b}.jsonl"), encoding="utf-8") as f:
        for j in map(json.loads, f):
            k = key[j["id"]]
            r = rows[j["id"]]
            for side in ("x", "y"):
                tag = k[side]
                g = j.get(side) or {}
                for crit in ("understood", "in_role", "language", "facts"):
                    v = g.get(crit)
                    if v is not None:
                        per[(tag, r["lang"], r["role"])][crit] += 1 if v else 0
                        per[(tag, r["lang"], r["role"])][crit + "_n"] += 1
                per[(tag, r["lang"], r["role"])]["good"] += 1 if g.get("good") else 0
                per[(tag, r["lang"], r["role"])]["n"] += 1
            pref = j.get("better")
            winner = k[pref] if pref in ("x", "y") else "tie"
            per[("pref", r["lang"], r["role"])][winner] += 1
    for (tag, lang, role), c in sorted(per.items()):
        if tag == "pref":
            print(f"preferred {lang} {role}: {dict(c)}")
        else:
            parts = [f"good {c['good']}/{c['n']}"] + [f"{k} {c[k]}/{c[k + '_n']}" for k in ("understood", "in_role", "language", "facts") if c[k + "_n"]]
            print(f"{tag:8} {lang} {role:6}: " + ", ".join(parts))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "answer":
        answer(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "gpu")
    elif cmd == "pairs":
        pairs(sys.argv[2], sys.argv[3])
    elif cmd == "score":
        score(sys.argv[2], sys.argv[3])
    elif cmd == "auto":
        auto(sys.argv[2])
