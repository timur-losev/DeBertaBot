#!/usr/bin/env bash
# After run_build_v54.sh: the gate and the threshold with the out-of-fold check, the export for C++, the test files,
# the C++ checks and the owner's spoken lines.
#   cd scripts/coop/stt && bash after_build_v54.sh
# PY=/path/to/python and CLI=/path/to/coop_cli override the defaults (the active environment; cpp/coop_intent/build).
# Without the three out-of-fold results it still makes a bot to try: quick_config_v54.py gives it bot v53's gate and
# threshold, and says so in bot_config.json -- run the out-of-fold runs and this script again for the real ones.
set -u
cd "$(dirname "$0")"
PY="${PY:-python}"
ROOT="$(cd ../../.. && pwd)"
BOT="$ROOT/models/coop-deberta-v3-ens3-v54"
CLI="${CLI:-$ROOT/cpp/coop_intent/build/coop_cli}"
for seed in 0 1 2; do
  [ -f "$BOT/seed$seed/model.safetensors" ] || { echo "no final model of seed $seed: run_build_v54.sh first"; exit 1; }
done
echo "==== score"
if [ -f finaloof54_0.json ] && [ -f finaloof54_1.json ] && [ -f finaloof54_2.json ]; then
  "$PY" score_v54.py | tee score_v54.log
  "$PY" kinds_v54.py | tee score_v54_kinds.log
else
  echo "the out-of-fold results are not all there: a provisional bot_config.json"
  "$PY" quick_config_v54.py || exit 1
fi
cd ..
echo "==== export"
"$PY" export_cpp.py "$BOT" | tail -1
echo "==== onnx check"
"$PY" check_onnx.py "$BOT" | tail -1
echo "==== test files"
"$PY" "$ROOT/cpp/coop_intent/tools/gen_tests.py" "$BOT" | tail -5
echo "==== C++ checks"
if [ -x "$CLI" ]; then
  for t in --tokenizer-tests --location-tests --gate-tests --decide-tests --golden --dialogue; do
    "$CLI" --model-dir "$BOT/cpp" $t | tail -1
  done
else
  echo "no $CLI: build the engine (HANDOFF.md, section 3), then run the six checks with --model-dir $BOT/cpp"
fi
echo "==== the owner's spoken lines"
for f in owner_voice_20261009.json owner_voice_20261009b.json owner_voice_20261009c.json; do
  COOP_DEVICE=cpu "$PY" owner_voice.py "$BOT" "$f" | grep -E "^ +(ok|NO)|^coop-"
done | tee owner_voice_v54.log
echo "==== the typed probe (probe_v54.txt; bot v53 on it: probe_v54_on_v53.log)"
COOP_DEVICE=cpu "$PY" probe_v54.py "$BOT" | grep -E "^ +(ok|NO)|^coop-" | tee probe_v54.log
