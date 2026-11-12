# Round v70's measures on the game's path (coop_cli --serve, the decoder on the CPU and on every line, as the game runs it since
# 2026-11-06), one brain: the new test (driving, the body's commands, combos), the owner test, test67, test66, the things of v68,
# the timer test, the memory scenarios and the owner's real lines replayed. Below-normal priority, 4-6 CPU threads; logs here.
#   pwsh measure_all_v70.ps1 -Tag v69s5n70     (the deployed brain: bot v67 + decoder v69s5, on today's coop_cli)
#   pwsh measure_all_v70.ps1 -Tag v70          (bot v70 + decoder v70)
#   pwsh measure_all_v70.ps1 -Tag v70b         (bot v70b + decoder v70);  -Tag v70c (bot v70c + decoder v70)
param([Parameter(Mandatory = $true)][ValidateSet('v69s5n70', 'v70', 'v70b', 'v70c')][string]$Tag)
$ErrorActionPreference = 'Continue'
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$env:PYTHONIOENCODING = 'utf-8'
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$stt = Join-Path $PSScriptRoot '..\..'
$v69 = Join-Path $stt 'chains2\ml_v69'
$models = 'G:\Proj\ollaya\DeBertaBot\models'
$chain, $botName = switch ($Tag) {
    'v70' { 'v70', 'coop-deberta-v3-ens3-v70' }
    'v70b' { 'v70', 'coop-deberta-v3-ens3-v70b' }      # bot v70b: the canon's turns among the seeds
    'v70c' { 'v70', 'coop-deberta-v3-ens3-v70c' }      # bot v70c: + the decoder's own "turn left" as LOOK_AT
    default { 'v69s5', 'coop-deberta-v3-ens3-v67' }
}
$chainDir = "$models\coop-chain-$chain\cpp"
$env:COOP_BOT = "$models\$botName\cpp"
$env:COOP_EVERY_LINE = '1'
$log = Join-Path $PSScriptRoot "measure_all_$Tag.log"
"{0:HH:mm:ss}  start $Tag (chain $chain, bot $botName, every line)" -f (Get-Date) | Out-File $log -Encoding utf8
# the new test (its own log measure_v70_new_<chain>.log)
Push-Location $PSScriptRoot; & $jev measure_v70_new.py "$Tag=$chain" $botName 2>&1 | Select-String 'on test_v70_new' | Out-File $log -Append -Encoding utf8; Pop-Location
# the owner test of round v69 (its log measure_v69_owner_<Tag>.log in ml_v69, copied here)
Push-Location $v69; & $jev measure_v69_owner.py "$Tag=$chain" 2>&1 | Select-String 'owner test' | Out-File $log -Append -Encoding utf8
Copy-Item "measure_v69_owner_$Tag.log" (Join-Path $PSScriptRoot "measure_v69_owner_$Tag.log") -Force; Pop-Location
Push-Location $stt; & $jev measure_v67_cli.py $Tag 2>&1 | Select-String 'on test67' | Out-File $log -Append -Encoding utf8; Pop-Location
Push-Location (Join-Path $stt 'chains2\ml_v68'); & $jev measure_v66_cli.py $Tag 2>&1 | Select-String 'on test66' | Out-File $log -Append -Encoding utf8
& $jev measure_v68_things.py $Tag 2>&1 | Select-String 'on test68' | Out-File $log -Append -Encoding utf8
& $jev measure_v68_time.py $chainDir $Tag 2>&1 | Select-Object -Last 6 | Out-File $log -Append -Encoding utf8; Pop-Location
# the memory scenarios (teaching: the decoder must leave them alone) with this bot and chain, the chain in every scenario
Push-Location (Join-Path $stt '..'); & $jev memory_tests.py --bot $env:COOP_BOT --chain $chainDir --decoder-every-line --all-chain 2>&1 |
    Out-File (Join-Path $PSScriptRoot "memory_tests_$Tag.log") -Encoding utf8
Get-Content (Join-Path $PSScriptRoot "memory_tests_$Tag.log") -Tail 1 | Out-File $log -Append -Encoding utf8; Pop-Location
# ... and as round v69 ran them (the chain only where a scenario asks for it, English lines to the classifier)
Push-Location (Join-Path $stt '..'); & $jev memory_tests.py --bot $env:COOP_BOT --chain $chainDir 2>&1 |
    Out-File (Join-Path $PSScriptRoot "memory_tests_${Tag}_v69flags.log") -Encoding utf8
Get-Content (Join-Path $PSScriptRoot "memory_tests_${Tag}_v69flags.log") -Tail 1 | Out-File $log -Append -Encoding utf8; Pop-Location
# the owner's real lines replayed (replay_owner_talk_<Tag>.jsonl in ml_v69); the diff once both tags are there
Push-Location $v69; & $jev replay_owner_talk.py "$Tag=$chain" 2>&1 | Select-Object -Last 1 | Out-File $log -Append -Encoding utf8
if ($Tag -ne 'v69s5n70' -and (Test-Path 'replay_owner_talk_v69s5n70.jsonl') -and (Test-Path "replay_owner_talk_$Tag.jsonl")) {
    & $jev replay_owner_talk.py --diff v69s5n70 $Tag 2>&1 | Out-File (Join-Path $PSScriptRoot "talk_diff_v69s5n70_$Tag.txt") -Encoding utf8
    Get-Content (Join-Path $PSScriptRoot "talk_diff_v69s5n70_$Tag.txt") -Tail 1 | Out-File $log -Append -Encoding utf8
}
Pop-Location
"{0:HH:mm:ss}  done $Tag" -f (Get-Date) | Out-File $log -Append -Encoding utf8
