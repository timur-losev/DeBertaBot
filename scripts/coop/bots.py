"""
Which trained bot the Python tools use when none is named: one constant, the single switch.

  coop-deberta-v3-ens3-v2    v2, the shipped bot: 24 intents, no place lines in training
  coop-deberta-v3-ens3-v3    v3: trained with lines that name map places (the model in the repository
                             was trained on the Mac, MPS). Not the default: it carries out smoke and
                             "clear" callouts as orders (HANDOFF.md, section 4)
  coop-deberta-v3-ens3-v31   v3 re-trained with seed set v31 (make_seeds_v31.py), on the work machine:
                             roof orders are MOVE_TO, smoke and "clear" callouts are left alone. The
                             candidate for the default; no blind number yet (HANDOFF.md, section 4)

Switching the default is the owner's decision (HANDOFF.md, section 7): change DEFAULT here and
COOP_MODEL_DIR in cpp/coop_intent/CMakeLists.txt (a CMake cache variable: an existing build
directory keeps the old value).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "models"))
DEFAULT = "coop-deberta-v3-ens3-v2"


def default_bot():
    return os.path.join(MODELS, DEFAULT)
