"""
Which trained bot the Python tools use when none is named: one constant, the single switch.

  coop-deberta-v3-ens3-v31   the default since 2026-10-04 (the owner's decision): v3 re-trained with
                             seed set v31 (make_seeds_v31.py), on the work machine. Roof orders are
                             MOVE_TO, smoke and "clear" callouts are left alone. No blind number yet
                             (HANDOFF.md, section 4)
  coop-deberta-v3-ens3-v3    v3: trained with lines that name map places and the first seed set (the
                             model in the repository was trained on the Mac, MPS). It carries out
                             smoke and "clear" callouts as orders
  coop-deberta-v3-ens3-v2    v2, the default until then: 24 intents, no place lines in training

Model weights are not in git, so a machine may not have the default bot's (HANDOFF.md, section 1).
Then the tools take FALLBACK and say so on stderr.

To switch the default: change DEFAULT here and the same name in cpp/coop_intent/CMakeLists.txt
(COOP_MODEL_DIR is a CMake cache variable: an existing build directory keeps the old value).
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "models"))
DEFAULT = "coop-deberta-v3-ens3-v31"
FALLBACK = "coop-deberta-v3-ens3-v2"


def has_weights(model_dir):
    """The bot's PyTorch weights are on this machine (every member's model.safetensors)."""
    cfg = os.path.join(model_dir, "bot_config.json")
    if not os.path.exists(cfg):
        return False
    members = json.load(io.open(cfg, encoding="utf-8")).get("members", ["."])
    return all(os.path.exists(os.path.join(model_dir, m, "model.safetensors")) for m in members)


def default_bot():
    d, f = os.path.join(MODELS, DEFAULT), os.path.join(MODELS, FALLBACK)
    if not has_weights(d) and has_weights(f):
        print(f"bots.py: the weights of the default bot ({DEFAULT}) are not on this machine; using {FALLBACK}",
              file=sys.stderr)
        return f
    return d
