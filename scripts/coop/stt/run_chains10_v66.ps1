# Decoder v66 (chains10_v66.py train, then gguf), below-normal priority; log chains10_v66.log next to this file.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$env:PYTHONIOENCODING = 'utf-8'
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
"{0:HH:mm:ss}  train start" -f (Get-Date) | Out-File chains10_v66.log -Append -Encoding utf8
& $jev chains10_v66.py train 0 2>&1 | Where-Object { $_ -notmatch 'Loading weights|it/s\]' } | Out-File chains10_v66.log -Append -Encoding utf8
"{0:HH:mm:ss}  train end, gguf" -f (Get-Date) | Out-File chains10_v66.log -Append -Encoding utf8
& $jev chains10_v66.py gguf 0 2>&1 | Select-Object -Last 5 | Out-File chains10_v66.log -Append -Encoding utf8
"{0:HH:mm:ss}  done" -f (Get-Date) | Out-File chains10_v66.log -Append -Encoding utf8
