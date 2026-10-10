#!/usr/bin/env bash
# Bot v54, all of its training, for the MacBook (bash; Linux too): the three final models first -- they are the bot --,
# then the three out-of-fold runs (five trainings each), which give the gate, the threshold and the check.
#   cd scripts/coop/stt && bash run_build_v54.sh       # one process at a time
#   JOBS=2 bash run_build_v54.sh                       # two at a time, if the memory allows (count 5 GB a process)
#   ONLY=final bash run_build_v54.sh                   # the bot only;  ONLY=oof: the check only
# The Python is the project's environment (HANDOFF.md, section 2): activate it first, or pass PY=/path/to/python.
# The device is cuda, else mps, else cpu (COOP_DEVICE overrides). microsoft/deberta-v3-base comes from the Hugging
# Face cache or the network. A run that was cut short goes on where it stopped: a finished model is skipped, an
# out-of-fold run keeps its finished folds (finaloof54_<seed>.part.json). Logs: build_v54_<mode>_<seed>.log next to
# this file. Afterwards: bash after_build_v54.sh
set -u
cd "$(dirname "$0")"
PY="${PY:-python}"
JOBS="${JOBS:-1}"
ONLY="${ONLY:-}"
BOT=../../../models/coop-deberta-v3-ens3-v54
KEEP=""
command -v caffeinate >/dev/null 2>&1 && KEEP="caffeinate -i"     # macOS: no sleep while a training runs
"$PY" -c "import torch, transformers, sentencepiece" || { echo "this Python lacks torch, transformers or sentencepiece: $PY"; exit 1; }
"$PY" -c "import sys; sys.path.insert(0, '..'); import train_v2 as T; print('device:', T.pick_device())" || exit 1
todo=""
for seed in 0 1 2; do
  if [ "$ONLY" != "oof" ] && [ ! -f "$BOT/seed$seed/model.safetensors" ]; then todo="$todo final:$seed"; fi
done
for seed in 0 1 2; do
  if [ "$ONLY" != "final" ] && [ ! -f "finaloof54_$seed.json" ]; then todo="$todo oof:$seed"; fi
done
if [ -z "$todo" ]; then echo "nothing to do: the models and the out-of-fold results are there"; exit 0; fi
echo "to run, $JOBS at a time:$todo"
start=$(date +%s)
# each job goes to sh as its argument ($1): BSD xargs (macOS) does not substitute -I{} into a long command
printf '%s\n' $todo | PY="$PY" KEEP="$KEEP" xargs -P "$JOBS" -n 1 sh -c '
  job="$1"; mode="${job%%:*}"; seed="${job##*:}"; log="build_v54_${mode}_${seed}.log"
  echo "started $mode $seed"
  if $KEEP "$PY" build_v54.py "$mode" "$seed" >> "$log" 2> "$log.err"; then echo "finished $mode $seed: $(tail -1 "$log")"
  else echo "FAILED $mode $seed: see $log.err"; fi
' sh
echo "done in $(( $(date +%s) - start )) s"
for seed in 0 1 2; do
  [ -f "$BOT/seed$seed/model.safetensors" ] || echo "MISSING: the final model of seed $seed"
  [ -f "finaloof54_$seed.json" ] || echo "missing: the out-of-fold run of seed $seed"
done
