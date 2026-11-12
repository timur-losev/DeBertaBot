# The v70 voice chain (2026-10-27): seeds only, v70 adds no lines: the lists (export_v70.py), the Windows voices (synth_windows_v70.ps1),
# Kokoro and VCTK (synth_v70.py, in the speech venv), then Parakeet TDT 0.6B v2 on every new folder's files ->
# out_parakeet-0.6b-v2_<condition>_v70.json, which build_v70.py reads. Below-normal priority: an editor may be open beside it.
#   pwsh run_voices_v70.ps1            # log: voices_v70.log next to this file
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$venv = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
$log = Join-Path $PSScriptRoot 'voices_v70.log'
function Step($name, [scriptblock]$what) {
    $t = Get-Date
    $out = & $what 2>&1 | Out-String
    "{0:HH:mm:ss}  {1,-22} {2,5:n0} s  {3}" -f (Get-Date), $name, ((Get-Date) - $t).TotalSeconds, ($out.Trim() -split "`n" | Select-Object -Last 1) | Tee-Object -FilePath $log -Append
}
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
"{0:HH:mm:ss}  start" -f (Get-Date) | Tee-Object -FilePath $log -Append
Step 'export seeds' { & $jev export_v70.py seeds }
Step 'windows seeds' { pwsh -NoProfile -File synth_windows_v70.ps1 seeds }
Step 'piper/kokoro seeds' { & $venv synth_v70.py seeds }
$env:STT_THREADS = '4'
foreach ($c in 'seedclean', 'seedkokoro', 'seedkokorox', 'seedvctkA') {
    $env:STT_LINES = 'seeds_v70.json'
    Step "stt $c" { & $venv run_stt.py parakeet-0.6b-v2 $c --tag _v70 }
}

"{0:HH:mm:ss}  done" -f (Get-Date) | Tee-Object -FilePath $log -Append
