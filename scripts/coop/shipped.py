"""
The shipped bot's classifier as a function: probabilities for a list of lines, from the model
directory coop_bot.py uses (an ensemble averages its members). For studies that ask "what does the
bot in the game answer to this line" (eval_v3.py, v3_noharm.py).

    import shipped; P = shipped.Predictor(); probs = P(["hold the north door"])
"""
import io, json, os

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "models", "coop-deberta-v3-ens3-v2"))


class Predictor:
    def __init__(self, model_dir=MODEL_DIR, device=None):
        self.cfg = json.load(io.open(os.path.join(model_dir, "bot_config.json"), encoding="utf-8"))
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        dirs = [os.path.join(model_dir, m) for m in self.cfg.get("members", ["."])]
        self.tok = AutoTokenizer.from_pretrained(dirs[0])
        self.models = [AutoModelForSequenceClassification.from_pretrained(d, dtype=torch.float32).eval().to(self.device)
                       for d in dirs]
        self.labels = self.cfg["labels"]

    def __call__(self, texts, batch=64):
        out = []
        with torch.no_grad():
            for b in range(0, len(texts), batch):
                x = self.tok(texts[b:b + batch], truncation=True, max_length=64, padding=True, return_tensors="pt")
                x = {k: v.to(self.device) for k, v in x.items()}
                p = torch.stack([torch.softmax(m(**x).logits.float(), -1) for m in self.models]).mean(0)
                out += p.cpu().tolist()
        return out
