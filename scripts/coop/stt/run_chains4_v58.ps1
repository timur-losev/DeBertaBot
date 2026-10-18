# Round five of the chains study (chains4_v58.py, router_v58.py; chain v58 over bot v57), all of it in order, one training on
# the GPU at a time. Logs next to this file. Expected on the RTX 4090 and the i9-10900K: the voices 10-20 min (CPU, idle
# priority), the decoder about 35 min (round four: 16 832 rows in 1 786 s), the router 3 min, GGUF and export 5 min, the
# scores 10 min (the owner's set on the CPU decoder).
#   pwsh run_chains4_v58.ps1                  everything
#   pwsh run_chains4_v58.ps1 -From check      the v58 items are voiced already
#   pwsh run_chains4_v58.ps1 -From score      trained and exported: the tables only
# Before it: chains2\ctx_teacher_v58_r6.json, _cs.json, _stt.json (the blind authors' items), chains2\owner_ctx_v58.json (the
# owner's lines, a test set), the speech tools' environment in venv\, llama.cpp under models\llama.cpp, a build of coop_cli
# with the planner of 2026-10-18 (cpp\coop_intent\build\Release). Check nvidia-smi first: the owner may be playing.
param([ValidateSet('voice', 'check', 'train', 'score')]$From = 'voice')
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$voice = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$cli = Join-Path $repo 'cpp\coop_intent\build\Release\coop_cli.exe'
$bot = Join-Path $repo 'models\coop-deberta-v3-ens3-v57\cpp'
if (-not $env:HF_HUB_OFFLINE) { $env:HF_HUB_OFFLINE = '1' }
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $PSScriptRoot
$t0 = Get-Date
$order = 'voice', 'check', 'train', 'score'
function From($step) { $order.IndexOf($step) -ge $order.IndexOf($From) }
function Step($exe, $log, $cmd) {
    & $exe @cmd > $log 2> "$log.err"
    $code = $LASTEXITCODE
    "{0,6:n0} s  {1} (exit {2})" -f ((Get-Date) - $t0).TotalSeconds, ($cmd -join ' '), $code
    if ($code -ne 0) { throw "step failed: $($cmd -join ' ') (exit $code), see $log.err" }
}
if (From 'voice') {
    # what Parakeet hears of the r6 and cs items, from the four training voices (an stt item is a transcript already)
    Step $voice 'chains4_58_voice.log' @('voice_chains.py', 'train', 'chains2\ctx_teacher_v58_heard.json', 'chains2\ctx_teacher_v58_r6.json', 'chains2\ctx_teacher_v58_cs.json')
    Step $voice 'chains4_58_voice.log' @('voice_chains.py', 'train2', 'chains2\ctx_teacher_v58_heard.json', 'chains2\ctx_teacher_v58_r6.json', 'chains2\ctx_teacher_v58_cs.json')
}
if (From 'check') { Step $py 'chains4_58_check.log' @('chains4_v58.py', 'check') }
if (From 'train') {
    Step $py 'chains4_58_train_0.log' @('chains4_v58.py', 'train', '0')
    Step $py 'router58_train_final_small.log' @('router_v58.py', 'train', 'final', 'small', '0')
    Step $py 'chains4_58_gguf_0.log' @('chains4_v58.py', 'gguf', '0')
    Step $py 'chains4_58_export_0.log' @('chains4_v58.py', 'export', '0')
}
Step $py 'chains4_58_score.log' @('chains4_v58.py', 'score')
# the owner's lines end to end: the game's chain now (v55) and this round's (v58), the same engine and bot
Step $py 'owner_ctx_58_chain55.log' @('owner_ctx_score.py', $cli, $bot, (Join-Path $repo 'models\coop-chain-v55\cpp'), 'chains2\owner_ctx_v58_score_chain55.json')
Step $py 'owner_ctx_58_chain58.log' @('owner_ctx_score.py', $cli, $bot, (Join-Path $repo 'models\coop-chain-v58\cpp'), 'chains2\owner_ctx_v58_score_chain58.json')
Get-Content 'chains4_58_score.log'
Select-String -Path 'owner_ctx_58_chain55.log', 'owner_ctx_58_chain58.log' -Pattern 'read as expected'
"{0:n0} s in all" -f ((Get-Date) - $t0).TotalSeconds
