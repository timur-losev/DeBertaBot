# The taught decoder (qlora_v54.py) and the chains study (chains_v54.py), all of it in order, one training on the GPU
# at a time: a 2B model in 4 bits takes 11-18 GB while it trains, and two of them push Windows into swapping video
# memory. Logs next to this file. About an hour and a half on the RTX 4090.
#   pwsh run_qlora_v54.ps1              everything
#   pwsh run_qlora_v54.ps1 -SkipFolds   the five folds are already in qlora54_qwen3_r16_s0.json
# Before it: pip install --no-deps peft bitsandbytes into the training environment. The base model is downloaded
# into models/hf on the first run (set HF_HUB_OFFLINE=0 for that run).
# The chains study also needs chains/teacher_lines.json, chains/blind_author.json and chains/blind_ann1.json,
# blind_ann2.json: lines written and read by blind AI authors under chains/spec_chain.json (frozen.txt has the hashes).
param([switch]$SkipFolds)
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
if (-not $env:HF_HUB_OFFLINE) { $env:HF_HUB_OFFLINE = '1' }
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $PSScriptRoot
$t0 = Get-Date
function Step($log, $cmd) {
    & $py @cmd > $log 2> "$log.err"
    "{0,6:n0} s  {1} (exit {2})" -f ((Get-Date) - $t0).TotalSeconds, ($cmd -join ' '), $LASTEXITCODE
}
if (-not $SkipFolds) { Step 'qlora54_folds_qwen3_0.log' @('qlora_v54.py', 'folds', 'qwen3', '0') }
Step 'chains54_train_composed_0.log' @('chains_v54.py', 'train', 'composed', '0')
if (Test-Path 'chains\teacher_lines.json') {
    Step 'chains54_check.log' @('chains_v54.py', 'check')
    Step 'chains54_train_teacher_0.log' @('chains_v54.py', 'train', 'teacher', '0')
}
Step 'qlora54_final_qwen3_0.log' @('qlora_v54.py', 'final', 'qwen3', '0')
Step 'qlora54_timing_qwen3_0.log' @('qlora_v54.py', 'timing', 'qwen3', '0')
Step 'qlora54_score.log' @('qlora_v54.py', 'score')
Step 'chains54_score.log' @('chains_v54.py', 'score')
