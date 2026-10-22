"""decider-2b (Mapika, Qwen3.5-2B-Base) as the co-op bot's intent reader: the prompt, the model, the split.

The research question (the owner, 2026-10-21): fine-tune decider-2b on the bot's data with LoRA, run it quantized if possible,
and compare precision and recall with the DeBERTa ensemble (bot v61).

decider answers a typed question in one forward pass: the logits of its own LM head at an "Answer: (" slot, restricted to
the option-label tokens. The prompt here is upstream's schema-first layout (decider v10 was trained on it,
decider_config.json "schema_first_trained": true), with the options in a fixed order:

    Question: <QUESTION>\nOptions:\n(A) follow me: follow me, stay with me, on me\n(B) ...   <- prefix, the same for every line
    \n\nContext:\n<the transcript>\n\nAnswer: (                                             <- suffix, about 10-25 tokens

so the prefix (about 700 tokens: attention KV and delta-net states) is computed once and only the line's own tokens are
new. Tokenization is upstream's own (decider/prompt.py in the model repo).

The split is build_v61.py's: groups = lines + seeds + owner lines, shuffled with Random(1000 + seed), fold f held out. The
same keys as finaloof61_<seed>.json: typed|<id>, <condition>|<id> for the spoken lines, owner|<id>.
"""
import io, json, os, sys, types

os.environ["COOP_TAG"] = "v61"                         # before coop_v2 is imported: the v6x line's 57 intents
HERE =os.path.dirname(os.path.abspath(__file__))
COOP = os.path.normpath(os.path.join(HERE, ".."))
STT = os.path.join(COOP, "stt")
SNAP = os.path.join(STT, "models", "hf", "models--Mapika--decider-2b", "snapshots", "9839cc9d908be16c5988c0d041034b5fdf82c7a2")
OUT = os.path.join(STT, "models_out", "decider")      # git-ignored: adapters, merged weights, GGUF (never committed)
RES = os.path.join(HERE, "results")
sys.path.insert(0, SNAP)                               # upstream's decider package (prompt.py)
sys.path.insert(0, COOP)

QUESTION = ("A player in a co-op shooter gives a voice order to their AI teammate, the bot. The context is what the "
            "speech-to-text heard; it often mishears words (\"should\" for \"shoot\", \"good\" for \"go\"). Which order "
            "did the player give?")


def intents():
    import coop_v2 as V
    d = json.load(io.open(os.path.join(COOP, "intents_v60.json"), encoding="utf-8"))
    assert list(V.INTENTS) == [k for k in d if not k.startswith("_")], "intent order"
    return list(V.INTENTS), [f"{d[k]['label']}: {d[k]['description']}" for k in V.INTENTS]


def tokenizer():
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(SNAP)


def prompt_parts(tok):
    """(prefix ids, label token ids of the 57 options, suffix(text) -> ids). The slot is the suffix's last token."""
    from decider.prompt import schema_prefix_ids, schema_suffix_ids, label_table
    labels, options = intents()
    q = types.SimpleNamespace(text=QUESTION, options=options, gold=0)
    pre = schema_prefix_ids(tok, [q], [list(range(len(options)))])
    lab = label_table(tok)[1][:len(options)]

    def suffix(text):
        ids, slots = schema_suffix_ids(tok, text, 1)
        assert slots == [len(ids) - 1]
        return ids
    return pre, lab, suffix


def split(seed=0, fold=0):
    """build_v61.py's out-of-fold split: (training rows, test rows). Rows: {id, text, maj}; test ids as in finaloof61."""
    os.environ["COOP_TAG"] = "v61"
    sys.path.insert(0, STT)
    import random
    import build_v61 as B
    groups = B.LINES + B.SEEDS + B.OWNER
    random.Random(1000 + seed).shuffle(groups)
    held = {g["id"] for g in groups[fold::5]}
    train = B.training_set([i for i in B.LINES if i["id"] not in held], [s for s in B.SEEDS if s["id"] not in held],
                           [o for o in B.OWNER if o["id"] not in held])
    test = [{"id": f"owner|{o['id']}", "text": o["text"], "maj": o["maj"]} for o in B.OWNER if o["id"] in held]
    for i in B.LINES:
        if i["id"] in held:
            test.append({"id": f"typed|{i['id']}", "text": i["text"], "maj": i["maj"]})
            if i["id"] in B.SPOKEN:
                test += [{"id": f"{c}|{i['id']}", "text": B.heard(c)[i["id"]], "maj": i["maj"]} for c in B.LINE_TEST]
    return train, test


def everything():
    """Every training row of build_v61.py's final models (all lines, seeds and owner lines, with their transcripts)."""
    sys.path.insert(0, STT)
    import build_v61 as B
    return B.training_set(B.LINES, B.SEEDS, B.OWNER)


# ---- the model ------------------------------------------------------------------------------------------------------

def load_model(path=SNAP, dtype="bfloat16", device="cuda"):
    import torch
    from transformers import AutoModelForCausalLM
    lm = AutoModelForCausalLM.from_pretrained(path, dtype=getattr(torch, dtype)).to(device)
    lm.config.use_cache = True
    return lm


def patch_cache_for_autograd():
    """transformers keeps the delta-net states in fixed buffers and updates them with copy_() (for CUDA graphs). A loss
    read after a cached prefix then fails in backward (a tensor saved for the gradient was overwritten). Assign instead."""
    import torch
    from transformers import cache_utils as cu
    L = cu.LinearAttentionLayer

    def update_conv_state(self, conv_states, state_idx=0, conv_kernel_size=None, **kw):
        if not self.is_conv_states_initialized[state_idx]:
            self.lazy_initialization(conv_states=conv_states, state_idx=state_idx, conv_kernel_size=conv_kernel_size)
        k = self.conv_kernel_size[state_idx]
        if not self.has_previous_state[state_idx]:
            full = conv_states
            self.has_previous_state[state_idx] = True
            if full.shape[-1] < k:
                full = torch.nn.functional.pad(full, (k - full.shape[-1], 0), value=0)
        else:
            full = torch.cat([self.conv_states[state_idx], conv_states], dim=-1)
        self.conv_states[state_idx] = full[..., -k:]
        return full

    def update_recurrent_state(self, recurrent_states, state_idx=0, **kw):
        if not self.is_recurrent_states_initialized[state_idx]:
            self.lazy_initialization(recurrent_states=recurrent_states, state_idx=state_idx)
        self.recurrent_states[state_idx] = recurrent_states
        return recurrent_states

    L.update_conv_state = update_conv_state
    L.update_recurrent_state = update_recurrent_state


def prefix_cache(lm, prefix_ids):
    """The cache after the prefix (batch 1); gradients flow through it when grad is enabled."""
    import torch
    from transformers import DynamicCache
    cache = DynamicCache(config=lm.config)
    x = torch.tensor([prefix_ids], device=lm.device)
    lm.model(input_ids=x, past_key_values=cache, use_cache=True)
    return cache


def expand(cache, n):
    """Repeat a batch-1 cache n times along the batch (new tensors, so autograd sees one prefix used n times)."""
    for layer in cache.layers:
        for d in (getattr(layer, "conv_states", None), getattr(layer, "recurrent_states", None)):
            if d:
                for k, v in d.items():
                    if v is not None:
                        d[k] = v.repeat_interleave(n, dim=0)
        if getattr(layer, "keys", None) is not None and layer.keys.numel():
            layer.keys = layer.keys.repeat_interleave(n, dim=0)
            layer.values = layer.values.repeat_interleave(n, dim=0)
    return cache


def label_logits(lm, prefix_ids, suffixes, lab_ids, pad_id=248044, prefix_grad=True):
    """[B, len(lab_ids)] logits at each suffix's slot (its last token), the prefix computed once for the batch. With
    prefix_grad=False the prefix runs without gradient (with the current LoRA weights): training then learns from the
    line's own tokens only, at a fraction of the memory and time."""
    import torch
    if prefix_grad:
        cache = prefix_cache(lm, prefix_ids)
    else:
        with torch.no_grad():
            cache = prefix_cache(lm, prefix_ids)
    cache = expand(cache, len(suffixes))
    T = max(len(s) for s in suffixes)
    x = torch.full((len(suffixes), T), pad_id, dtype=torch.long, device=lm.device)
    for b, s in enumerate(suffixes):
        x[b, :len(s)] = torch.tensor(s)
    h = lm.model(input_ids=x, past_key_values=cache, use_cache=True).last_hidden_state      # causal: right padding is harmless
    slot = torch.tensor([len(s) - 1 for s in suffixes], device=lm.device)
    hs = h[torch.arange(len(suffixes), device=lm.device), slot]
    W = lm.get_output_embeddings().weight[torch.tensor(lab_ids, device=lm.device)]
    return (hs @ W.T).float()


def full_label_logits(lm, prefix_ids, suffixes, lab_ids):
    """The same without the cache: every row whole (the reference for the cached path)."""
    import torch
    out = []
    for s in suffixes:
        x = torch.tensor([prefix_ids + s], device=lm.device)
        h = lm.model(input_ids=x).last_hidden_state[0, -1]
        W = lm.get_output_embeddings().weight[torch.tensor(lab_ids, device=lm.device)]
        out.append((h @ W.T).float())
    return torch.stack(out)
