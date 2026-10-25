"""The earlier lines that the v64 intents take (annot/v64/relabel_v64.json): the blind lines and the owner's heard lines read
before v64 as small talk, a see question or no order, that ask for a report ("how are you", "how's it going", "what do you
see") or about the bot's body ("are you okay", "are you hurt", "got any ammo"). Candidates by pattern, each one then read by
hand; this script writes the candidates, the reviewed decisions are in REVIEWED.

    python make_relabel_v64.py candidates      -> annot/v64/relabel_candidates_v64.json
    python make_relabel_v64.py write           -> annot/v64/relabel_v64.json (REVIEWED only)"""
import io, json, os, re, sys

os.environ["COOP_TAG"] = "v64"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coop_v2 as V   # noqa: E402

STATUS = re.compile(r"\b(how are you|how're you|how you doing|how are you doing|how's it going|how is it going|how are things|"
                    r"how's everything|what do you see|what can you see|what are you seeing|sitrep|status report|what's the situation|"
                    r"anything to report|see anything|anything on your end|what's around)\b", re.I)
BODY = re.compile(r"\b(are you (ok|okay|alright|all right|hurt|wounded|injured|hit|hot|cold|freezing|burning)|you (ok|okay|alright)|"
                  r"how do you feel|how's your health|your health|got (any )?ammo|how much ammo|low on ammo|out of ammo\?|"
                  r"can you breathe|smell gas)\b", re.I)
FROM = ("SMALL_TALK", "SEE_THING", "NONE", "MOVE_TO", "WAIT", "YES", "NO")

# the decisions, line by line (id -> intent, or None: stays), written after reading the candidates
REVIEWED = {
    "csv54_042": None,                                  # "don't crouch ... you can't see anything over the box": a negated order, WAIT
    "r6v62_002": ("STATUS_REPORT", ["SEE_THING"]),       # "You seeing anything on your end?": a report; the see question still fits
    "sttv62_012": ("STATUS_REPORT", []),                 # "hey buddy how's it going": how-are-you is the report (the owner)
    "sttv62_019": ("BODY_STATE", ["SMALL_TALK"]),        # "you still there um you okay": are-you-okay is the body
}


def candidates():
    items = V.load_items()
    owner = json.load(io.open(os.path.join(HERE, "owner_lines_v61.json"), encoding="utf-8"))["items"]
    out = []
    for it in items:
        if it["maj"] in FROM and (STATUS.search(it["text"]) or BODY.search(it["text"])):
            out.append({"id": it["id"], "text": it["text"], "from": it["maj"], "guess": "STATUS_REPORT" if STATUS.search(it["text"]) else "BODY_STATE", "kind": "line"})
    for o in owner:
        if o["maj"] in FROM and (STATUS.search(o["text"]) or BODY.search(o["text"])):
            out.append({"id": o["id"], "text": o["text"], "from": o["maj"], "guess": "STATUS_REPORT" if STATUS.search(o["text"]) else "BODY_STATE", "kind": "owner"})
    os.makedirs(os.path.join(HERE, "annot", "v64"), exist_ok=True)
    json.dump(out, io.open(os.path.join(HERE, "annot", "v64", "relabel_candidates_v64.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for c in out:
        print(f"{c['kind']:5} {c['id']:16} {c['from']:10} -> {c['guess']:13} {c['text']}")
    print(len(out), "candidates")


def write():
    cands = {c["id"]: c for c in json.load(io.open(os.path.join(HERE, "annot", "v64", "relabel_candidates_v64.json"), encoding="utf-8"))}
    lines, owner = {}, {}
    for cid, decision in REVIEWED.items():
        if decision is None:
            continue
        to, also = decision
        c = cands[cid]
        (owner if c["kind"] == "owner" else lines)[cid] = {"text": c["text"], "from": c["from"], "to": to, "also": also}
    json.dump({"note": "make_relabel_v64.py: earlier lines the v64 intents take, read one by one", "lines": lines, "owner": owner},
              io.open(os.path.join(HERE, "annot", "v64", "relabel_v64.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(lines)} lines, {len(owner)} owner lines relabelled")


if __name__ == "__main__":
    {"candidates": candidates, "write": write}[sys.argv[1]]()
