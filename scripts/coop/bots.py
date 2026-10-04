"""
Which trained bot the tools use when none is named: the newest one that exists under models/.

  coop-deberta-v3-ens3-v31   v3 re-trained with seed set v31 (make_seeds_v31.py); not trained yet when
                             this file was written -- `COOP_TAG=v31 python train_v2.py final ens3`
  coop-deberta-v3-ens3-v3    v3: trained with lines that name map places (COOP-BOT.md "v3")
  coop-deberta-v3-ens3-v2    v2: 24 intents, no place lines
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.normpath(os.path.join(HERE, "..", "..", "models"))
ORDER = ["coop-deberta-v3-ens3-v31", "coop-deberta-v3-ens3-v3", "coop-deberta-v3-ens3-v2"]


def default_bot():
    for name in ORDER:
        d = os.path.join(MODELS, name)
        if os.path.exists(os.path.join(d, "bot_config.json")):
            return d
    return os.path.join(MODELS, ORDER[1])
