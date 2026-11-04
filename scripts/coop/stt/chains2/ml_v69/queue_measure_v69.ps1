# Waits for a decoder run of round v69 to end (its log says "done (exit"), then measure_all_v69.ps1 on its tag.
#   pwsh queue_measure_v69.ps1                 (v69, chains13_v69.log)
#   pwsh queue_measure_v69.ps1 -Tag v69s2      (chains13_v69s2.log)
param([string]$Tag = 'v69')
$ErrorActionPreference = 'Continue'
$log = "G:\Proj\ollaya\DeBertaBot\scripts\coop\stt\chains13_$Tag.log"
while (-not ((Test-Path $log) -and (Select-String -Path $log -Pattern 'done \(exit' -Quiet))) {
    if ((Test-Path $log) -and (Select-String -Path $log -Pattern 'train failed|stopped on request' -Quiet)) { exit 1 }
    Start-Sleep -Seconds 30
}
& pwsh -NoProfile -File 'G:\Proj\ollaya\DeBertaBot\scripts\coop\stt\chains2\ml_v69\measure_all_v69.ps1' -Tag $Tag
