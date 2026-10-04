"""
laya:en rebuilt in PyTorch from ollaya's own files, so it can be fine-tuned like the DeBERTa bot.

Architecture, read off the shipped weights (safetensors blob) and ONNX graph:

  [CLS] <type> question: <instructions> [SEP] [MASK] opt0 [MASK] opt1 ... [SEP] <state> [SEP]
    -> ModernBERT-large encoder (encoder.*)
    -> + type_emb[qtype] added at every position       (choice 0, score 1, noul 2)
    -> 2 x nn.TransformerEncoderLayer(1024, 4096 ff, ReLU, pre-norm) over the whole sequence,
       key-padding mask from attention_mask             (head.layers.*)
    -> the hidden vector at each option's [MASK]
    -> scorer: LayerNorm -> Linear(1024,1024) -> GELU -> Linear(1024,1)   = one logit per option
  act_head (1024 [CLS] + 4 confidence features -> 256 -> 2) is loaded but not trained here.
  Probabilities = softmax(logits / T), T from the calibration blob by (type, option-count bucket),
  clamped to [0.5, 5.0] as ollaya does.

The sequence is built exactly as crates/ollaya-decision/src/layout.rs builds it (option text
"label: description", 48-token cap per option, the 192-token head budget, instructions cut last).

    python laya_torch.py --parity      # compare with the running ollaya daemon (laya:en)
"""
import io, json, os, sys

import torch
import torch.nn as nn
from safetensors.torch import load_file
from tokenizers import Tokenizer
from transformers import ModernBertConfig, ModernBertModel

BLOBS = r"G:\Proj\ollaya\install\models\blobs"
WEIGHTS = os.path.join(BLOBS, "sha256-891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c")
TOKENIZER = os.path.join(BLOBS, "sha256-6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30")
CALIB = os.path.join(BLOBS, "sha256-a7af5a5fafb5b418420a63511194038faed0aade75af68d210144e67fd792426")
CLS, SEP, MASK, PAD = 50281, 50282, 50284, 50283
MAX_LEN, HEAD_MAX = 512, 192
MAX_OPTION_TOKENS, MIN_HEAD_ROOM, MIN_INSTR, MIN_PER_OPT = 48, 16, 8, 4
QTYPE = {"choice": 0, "score": 1, "noul": 2}
NHEAD = int(os.environ.get("LAYA_NHEAD", "16"))


class Laya(nn.Module):
    def __init__(self, config_dir="answerdotai/ModernBERT-large"):
        super().__init__()
        # config_dir: a saved ModernBERT config (the fine-tuned model folder carries one), or the hub id
        self.encoder = ModernBertModel(ModernBertConfig.from_pretrained(config_dir))
        self.type_emb = nn.Embedding(3, 1024)
        layer = nn.TransformerEncoderLayer(1024, NHEAD, 4096, dropout=0.1, activation="relu",
                                           batch_first=True, norm_first=True)
        self.head = nn.TransformerEncoder(layer, num_layers=2, enable_nested_tensor=False)
        self.scorer = nn.Sequential(nn.LayerNorm(1024), nn.Linear(1024, 1024), nn.GELU(), nn.Linear(1024, 1))
        self.act_head = nn.Sequential(nn.Linear(1028, 256), nn.GELU(), nn.Linear(256, 2))
        self.temperature = nn.Parameter(torch.ones(3))

    def forward(self, input_ids, attention_mask, marker_pos, marker_mask, qtype):
        h = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        h = h + self.type_emb(qtype)[:, None, :]
        h = self.head(h, src_key_padding_mask=~attention_mask.bool())
        idx = marker_pos.clamp(min=0)[..., None].expand(-1, -1, h.size(-1))
        logits = self.scorer(torch.gather(h, 1, idx)).squeeze(-1)
        return logits.masked_fill(~marker_mask, -1e4)


def load_laya(path=WEIGHTS):
    model = Laya()
    sd = {k: v.float() for k, v in load_file(path).items()}
    missing, unexpected = model.load_state_dict(sd, strict=False)
    return model, missing, unexpected


class Encoder:
    """layout.rs, laya-markers-v1."""

    def __init__(self, tokenizer=TOKENIZER):
        self.tok = Tokenizer.from_file(tokenizer)
        self.calib = json.load(io.open(CALIB, encoding="utf-8"))

    def enc(self, s):
        return self.tok.encode(s, add_special_tokens=False).ids

    def build(self, state, instructions, criteria, qtype="choice"):
        options = [f"{k}: {v}" if v else k for k, v in criteria.items()]
        head = self.enc(f"{qtype} question: {instructions.replace('[MASK]', ' ')}")
        opt_ids = [[MASK] + self.enc(" " + o.replace("[MASK]", " "))[:MAX_OPTION_TOKENS] for o in options]
        budget = HEAD_MAX - sum(len(o) for o in opt_ids)
        if budget < MIN_HEAD_ROOM:
            per = max((HEAD_MAX - MIN_HEAD_ROOM) // len(opt_ids), MIN_PER_OPT)
            opt_ids = [o[:per] for o in opt_ids]
            budget = HEAD_MAX - sum(len(o) for o in opt_ids)
        head = head[:max(budget, MIN_INSTR)]
        ids = [CLS] + head + [SEP]
        markers = []
        for o in opt_ids:
            markers.append(len(ids))
            ids += o
        ids += [SEP]
        st = self.enc(state.replace("[MASK]", " "))
        room = MAX_LEN - len(ids) - 1
        ids = (ids + st[:max(room, 0)] + [SEP])[:MAX_LEN]
        return ids, [m for m in markers if m < MAX_LEN], list(criteria)

    def temperature(self, qtype, k):
        b = "2" if k == 2 else "3-5" if k <= 5 else "6-10" if k <= 10 else "11+"
        t = self.calib["temperature_by_options"].get(f"{qtype}:{b}", self.calib["temperature"][QTYPE[qtype]])
        return min(max(float(t), 0.5), 5.0)

    def batch(self, rows):
        """rows: list of (ids, markers, qtype_index) -> tensors, right-padded."""
        L = max(len(r[0]) for r in rows)
        K = max(len(r[1]) for r in rows)
        ids = torch.full((len(rows), L), PAD, dtype=torch.long)
        att = torch.zeros((len(rows), L), dtype=torch.long)
        mp = torch.zeros((len(rows), K), dtype=torch.long)
        mm = torch.zeros((len(rows), K), dtype=torch.bool)
        for i, (r_ids, r_m, _) in enumerate(rows):
            ids[i, :len(r_ids)] = torch.tensor(r_ids)
            att[i, :len(r_ids)] = 1
            mp[i, :len(r_m)] = torch.tensor(r_m)
            mm[i, :len(r_m)] = True
        qt = torch.tensor([r[2] for r in rows], dtype=torch.long)
        return ids, att, mp, mm, qt


def parity():
    """Same requests through this model and through ollaya; print the probability gap."""
    import urllib.request
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import run_coop as C
    model, missing, unexpected = load_laya()
    print(f"weights loaded: missing {len(missing)} {missing[:4]}, unexpected {len(unexpected)} {unexpected[:4]}")
    model.eval()
    E = Encoder()
    crit, back = C.wording("phrase")
    small = {"breach": "blow open the wall", "go now": "execute now", "not an order": "a callout or chatter"}
    lines = ["breach on my go", "come here", "two pushing through B apps", "hold the other angle",
             "cover me im crossing", "dont beach it"]
    worst = 0.0
    for criteria in (crit, small):
        for t in lines:
            state = f'Player said: "{t}"'
            ids, mk, labels = E.build(state, C.INSTR, criteria)
            with torch.no_grad():
                lg = model(*E.batch([(ids, mk, 0)]))[0, :len(labels)]
            p = torch.softmax(lg / E.temperature("choice", len(labels)), -1).tolist()
            body = {"model": "laya:en", "state": state, "keep_alive": "5m",
                    "questions": {"q": {"type": "choice", "instructions": C.INSTR, "criteria": criteria}}}
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                "http://127.0.0.1:11435/api/decide", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"}), timeout=300).read())
            q = r["answers"]["q"]["probabilities"]
            gap = max(abs(p[i] - q[labels[i]]) for i in range(len(labels)))
            worst = max(worst, gap)
            mine = labels[max(range(len(p)), key=p.__getitem__)]
            print(f"  {len(labels):>2} options  {t!r:<30} torch {mine:<14} {max(p):.3f} | ollaya "
                  f"{r['answers']['q']['choice']:<14} {max(q.values()):.3f} | max |dp| {gap:.4f}")
    print(f"worst probability gap: {worst:.4f}")


if __name__ == "__main__":
    if "--parity" in sys.argv:
        parity()
