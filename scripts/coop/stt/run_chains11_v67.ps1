# Decoder v67 (chains11_v67.py train, then gguf), below-normal priority; log chains11_v67.log next to this file.
# -Short: the same rows with the short system turn (chains11_v67.py ... short), log chains11_v67s.log.
# A snapshot every 30 minutes: after a crash or a stop, run this again and the training goes on from the last one.
# To free the GPU now without losing anything: pwsh stop_training.ps1 (a snapshot at the next step, then out).
param([switch]$Short)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$env:PYTHONIOENCODING = 'utf-8'
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$extra = @(if ($Short) { 'short' })
$log = if ($Short) { 'chains11_v67s.log' } else { 'chains11_v67.log' }
$me = if ($Short) { 'run_chains11_v67.ps1 -Short' } else { 'run_chains11_v67.ps1' }
"{0:HH:mm:ss}  train start" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains11_v67.py train 0 @extra 2>&1 | Where-Object { $_ -notmatch 'Loading weights|it/s\]' } | Out-File $log -Append -Encoding utf8
$code = $LASTEXITCODE
if ($code -eq 3) {
    "{0:HH:mm:ss}  stopped on request (snapshot taken); run $me again to go on" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit 3
}
if ($code -ne 0) {
    "{0:HH:mm:ss}  train failed (exit $code); run $me again to go on from the last snapshot" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit $code
}
"{0:HH:mm:ss}  train end, gguf" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains11_v67.py gguf 0 @extra 2>&1 | Select-Object -Last 5 | Out-File $log -Append -Encoding utf8
"{0:HH:mm:ss}  done" -f (Get-Date) | Out-File $log -Append -Encoding utf8
