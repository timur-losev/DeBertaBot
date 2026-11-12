# Decoder v70 (chains14_v70.py train, then gguf and export), below-normal priority; log chains14_v70.log next to this file.
# A snapshot every 30 minutes: after a crash or a stop, run this again and the training goes on from the last one.
# To free the GPU now without losing anything: pwsh stop_training.ps1 (a snapshot at the next step, then out).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$env:PYTHONIOENCODING = 'utf-8'
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$log = 'chains14_v70.log'
Remove-Item (Join-Path $PSScriptRoot 'STOP_TRAINING') -ErrorAction SilentlyContinue   # a stop asked of an earlier run
"{0:yyyy-MM-dd HH:mm:ss}  train start" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains14_v70.py train 0 2>&1 | Where-Object { $_ -notmatch 'Loading weights|it/s\]' } | Out-File $log -Append -Encoding utf8
$code = $LASTEXITCODE
if ($code -eq 3) {
    "{0:HH:mm:ss}  stopped on request (snapshot taken); run run_chains14_v70.ps1 again to go on" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit 3
}
if ($code -ne 0) {
    "{0:HH:mm:ss}  train failed (exit $code); run run_chains14_v70.ps1 again to go on from the last snapshot" -f (Get-Date) | Out-File $log -Append -Encoding utf8
    exit $code
}
"{0:HH:mm:ss}  train end, gguf" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains14_v70.py gguf 0 2>&1 | Select-Object -Last 5 | Out-File $log -Append -Encoding utf8
"{0:HH:mm:ss}  export" -f (Get-Date) | Out-File $log -Append -Encoding utf8
& $jev chains14_v70.py export 0 2>&1 | Select-Object -Last 8 | Out-File $log -Append -Encoding utf8
"{0:HH:mm:ss}  done (exit $LASTEXITCODE)" -f (Get-Date) | Out-File $log -Append -Encoding utf8
