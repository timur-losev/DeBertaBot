# Round six of the chains study (chains5_v59.py, router_v59.py; chain v59 over bot v58), all of it in order, one training on
# the GPU at a time. Logs next to this file. Expected on the RTX 4090 and the i9-10900K: the voices about 10 min (CPU, idle
# priority), the decoder about 40 min (round five: 2 400 s with the router), the router 3 min, GGUF and export 5 min, the scores
# 15 min (the owner's set of 50 on the CPU decoder, twice).
#   pwsh run_chains5_v59.ps1                  everything
#   pwsh run_chains5_v59.ps1 -From check      the v59 items are voiced already
#   pwsh run_chains5_v59.ps1 -From score      trained and exported: the tables only
# Before it: chains2\ctx_teacher_v59_r6.json, _cs.json, _stt.json (the blind authors' items), chains2\owner_ctx_v59.json (the
# owner's lines, a test set), the speech tools' environment in venv\, llama.cpp under models\llama.cpp, a build of coop_cli
# (cpp\coop_intent\build\Release). Check nvidia-smi first: the owner may be playing. The export takes round four's router (v55);
# set CHAINS5_ROUTER=coop-router-deberta-v3-small-v59 and run chains5_v59.py export again if router v59 scores better.
param([ValidateSet('voice', 'check', 'train', 'score')]$From = 'voice')
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$voice = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$cli = Join-Path $repo 'cpp\coop_intent\build\Release\coop_cli.exe'
$bot = Join-Path $repo 'models\coop-deberta-v3-ens3-v58\cpp'
if (-not $env:HF_HUB_OFFLINE) { $env:HF_HUB_OFFLINE = '1' }
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $PSScriptRoot
$t0 = Get-Date
$order = 'voice', 'check', 'train', 'score'
function From($step) { $order.IndexOf($step) -ge $order.IndexOf($From) }
function Step($exe, $log, $cmd, [switch]$Idle) {
    if ($Idle) {
        # the voices on the CPU at idle priority, the last six cores (the owner may be playing)
        $n = [Environment]::ProcessorCount
        $p = Start-Process -FilePath $exe -ArgumentList $cmd -WorkingDirectory $PSScriptRoot -PassThru -NoNewWindow -RedirectStandardOutput $log -RedirectStandardError "$log.err"
        try { $p.PriorityClass = 'Idle'; $p.ProcessorAffinity = [IntPtr]((([long]1 -shl 6) - 1) -shl ($n - 6)) } catch {}
        $p.WaitForExit()
        $code = $p.ExitCode
    } else {
        & $exe @cmd > $log 2> "$log.err"
        $code = $LASTEXITCODE
    }
    "{0,6:n0} s  {1} (exit {2})" -f ((Get-Date) - $t0).TotalSeconds, ($cmd -join ' '), $code
    if ($code -ne 0) { throw "step failed: $($cmd -join ' ') (exit $code), see $log.err" }
}
if (From 'voice') {
    # what Parakeet hears of the r6 and cs items, from the four training voices (an stt item is a transcript already)
    Step $voice 'chains5_59_voice.log' @('voice_chains.py', 'train', 'chains2\ctx_teacher_v59_heard.json', 'chains2\ctx_teacher_v59_r6.json', 'chains2\ctx_teacher_v59_cs.json') -Idle
    Step $voice 'chains5_59_voice2.log' @('voice_chains.py', 'train2', 'chains2\ctx_teacher_v59_heard.json', 'chains2\ctx_teacher_v59_r6.json', 'chains2\ctx_teacher_v59_cs.json') -Idle
}
if (From 'check') { Step $py 'chains5_59_check.log' @('chains5_v59.py', 'check') }
if (From 'train') {
    Step $py 'chains5_59_train_0.log' @('chains5_v59.py', 'train', '0')
    Step $py 'router59_train_final_small.log' @('router_v59.py', 'train', 'final', 'small', '0')
    Step $py 'chains5_59_gguf_0.log' @('chains5_v59.py', 'gguf', '0')
    Step $py 'chains5_59_export_0.log' @('chains5_v59.py', 'export', '0')
}
Step $py 'chains5_59_score.log.out' @('chains5_v59.py', 'score')
# the owner's lines end to end: the game's chain now (v58) and this round's (v59), the same engine and bot v58
$env:OWNER_CTX_SET = Join-Path $PSScriptRoot 'chains2\owner_ctx_v59.json'
Step $py 'owner_ctx_59_chain58.log' @('owner_ctx_score.py', $cli, $bot, (Join-Path $repo 'models\coop-chain-v58\cpp'), 'chains2\owner_ctx_v59_score_chain58.json')
Step $py 'owner_ctx_59_chain59.log' @('owner_ctx_score.py', $cli, $bot, (Join-Path $repo 'models\coop-chain-v59\cpp'), 'chains2\owner_ctx_v59_score_chain59.json')
Get-Content 'chains5_59_score.log'
Select-String -Path 'owner_ctx_59_chain58.log', 'owner_ctx_59_chain59.log' -Pattern 'read as expected'
"{0:n0} s in all" -f ((Get-Date) - $t0).TotalSeconds
