# Round v69's measures on the game's path (coop_cli --serve, the decoder on the CPU), one tag: the owner test, test67, test66,
# the new things of v68, the timer test. Below-normal priority, 4-6 CPU threads; logs next to each script.
#   pwsh measure_all_v69.ps1 -Tag v68s2now     (the deployed decoder on today's coop_cli)
#   pwsh measure_all_v69.ps1 -Tag v69
param([Parameter(Mandatory = $true)][string]$Tag)
$ErrorActionPreference = 'Continue'
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$env:PYTHONIOENCODING = 'utf-8'
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$stt = Join-Path $PSScriptRoot '..\..'
$chain = if ($Tag -like 'v68s2*') { 'v68s2' } else { $Tag }
$chainDir = "G:\Proj\ollaya\DeBertaBot\models\coop-chain-$chain\cpp"
$log = Join-Path $PSScriptRoot "measure_all_$Tag.log"
"{0:HH:mm:ss}  start $Tag" -f (Get-Date) | Out-File $log -Encoding utf8
Push-Location $PSScriptRoot; & $jev measure_v69_owner.py $chain 2>&1 | Select-Object -First 1 | Out-File $log -Append -Encoding utf8; Pop-Location
Push-Location $stt; & $jev measure_v67_cli.py $Tag 2>&1 | Select-Object -Last 4 | Out-File $log -Append -Encoding utf8; Pop-Location
Push-Location (Join-Path $stt 'chains2\ml_v68'); & $jev measure_v66_cli.py $Tag 2>&1 | Select-Object -First 1 | Out-File $log -Append -Encoding utf8
& $jev measure_v68_things.py $Tag 2>&1 | Select-Object -Last 4 | Out-File $log -Append -Encoding utf8
& $jev measure_v68_time.py $chainDir $Tag 2>&1 | Select-Object -Last 6 | Out-File $log -Append -Encoding utf8; Pop-Location
# the memory scenarios with this chain (teaching the decoder must leave alone; v69s2 failed 27 steps) and the owner's 495 real lines
# replayed (compare with replay_owner_talk.py --diff v68s2 <Tag>)
Push-Location (Join-Path $stt '..'); & $jev memory_tests.py --chain $chainDir 2>&1 | Out-File (Join-Path $PSScriptRoot "memory_tests_$Tag.log") -Encoding utf8
Get-Content (Join-Path $PSScriptRoot "memory_tests_$Tag.log") -Tail 1 | Out-File $log -Append -Encoding utf8; Pop-Location
Push-Location $PSScriptRoot; & $jev replay_owner_talk.py $chain 2>&1 | Select-Object -Last 1 | Out-File $log -Append -Encoding utf8
& $jev replay_owner_talk.py --diff v68s2 $chain 2>&1 | Out-File "talk_diff_v68s2_$chain.txt" -Encoding utf8
Get-Content "talk_diff_v68s2_$chain.txt" -Tail 1 | Out-File $log -Append -Encoding utf8; Pop-Location
"{0:HH:mm:ss}  done $Tag" -f (Get-Date) | Out-File $log -Append -Encoding utf8
