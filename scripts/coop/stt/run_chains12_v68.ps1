# Decoder v68s (chains12_v68.py train, then gguf and export), below-normal priority; log chains12_v68s<Run>.log next to this file.
# -Run 2: the second run, v68s2 (chains12_v68.py reads V68_RUN). Rerun with the same -Run to go on after a stop.
# A snapshot every 30 minutes: after a crash or a stop, run this again and the training goes on from the last one.
# To free the GPU now without losing anything: pwsh stop_training.ps1 (a snapshot at the next step, then out).
param([string]$Run = '')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$env:PYTHONIOENCODING = 'utf-8'
$env:V68_RUN = $Run
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$log = "chains12_v68s$Run.log"
Remove-Item (Join-Path $PSScriptRoot 'STOP_TRAINING') -ErrorAction SilentlyContinue   # a stop asked of an earlier run
"{0:yyyy-MM-dd HH:mm:ss}  train start" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains12_v68.py train 0 2>&1 | Where-Object { $_ -notmatch 'Loading weights|it/s\]' } | Out-File $log -Append -Encoding utf8
$code = $LASTEXITCODE
if ($code -eq 3) {
    "{0:HH:mm:ss}  stopped on request (snapshot taken); run run_chains12_v68.ps1 again to go on" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit 3
}
if ($code -ne 0) {
    "{0:HH:mm:ss}  train failed (exit $code); run run_chains12_v68.ps1 again to go on from the last snapshot" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit $code
}
"{0:HH:mm:ss}  train end, gguf" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains12_v68.py gguf 0 2>&1 | Select-Object -Last 5 | Out-File $log -Append -Encoding utf8
"{0:HH:mm:ss}  export" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains12_v68.py export 0 2>&1 | Select-Object -Last 8 | Out-File $log -Append -Encoding utf8
"{0:HH:mm:ss}  done (exit $LASTEXITCODE)" -f (Get-Date) | Out-File $log -Append -Encoding utf8
