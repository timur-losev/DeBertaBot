# Decoder v69 (chains13_v69.py train, then gguf and export), below-normal priority; log chains13_v69.log next to this file.
# -Run 2: v69s2 (V69_RUN=2, log chains13_v69s2.log).
# A snapshot every 30 minutes: after a crash or a stop, run this again and the training goes on from the last one.
# To free the GPU now without losing anything: pwsh stop_training.ps1 (a snapshot at the next step, then out).
param([string]$Run = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$env:PYTHONIOENCODING = 'utf-8'
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$env:V69_RUN = $Run
$log = if ($Run) { "chains13_v69s$Run.log" } else { "chains13_v69.log" }
Remove-Item (Join-Path $PSScriptRoot 'STOP_TRAINING') -ErrorAction SilentlyContinue   # a stop asked of an earlier run
"{0:yyyy-MM-dd HH:mm:ss}  train start" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains13_v69.py train 0 2>&1 | Where-Object { $_ -notmatch 'Loading weights|it/s\]' } | Out-File $log -Append -Encoding utf8
$code = $LASTEXITCODE
if ($code -eq 3) {
    "{0:HH:mm:ss}  stopped on request (snapshot taken); run run_chains13_v69.ps1 (with the same -Run) again to go on" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit 3
}
if ($code -ne 0) {
    "{0:HH:mm:ss}  train failed (exit $code); run run_chains13_v69.ps1 (with the same -Run) again to go on from the last snapshot" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit $code
}
"{0:HH:mm:ss}  train end, gguf" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains13_v69.py gguf 0 2>&1 | Select-Object -Last 5 | Out-File $log -Append -Encoding utf8
"{0:HH:mm:ss}  export" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains13_v69.py export 0 2>&1 | Select-Object -Last 8 | Out-File $log -Append -Encoding utf8
"{0:HH:mm:ss}  done (exit $LASTEXITCODE)" -f (Get-Date) | Out-File $log -Append -Encoding utf8
