# The v64 voice chain, all of it in order (2026-10-25): the lists (export_v64.py), the Windows voices (synth_windows_v64.ps1),
# Kokoro and VCTK (synth_v64.py, in the speech venv), then Parakeet TDT 0.6B v2 on every new folder's files ->
# out_parakeet-0.6b-v2_<condition>_v64.json, which build_v64.py reads. Below-normal priority: an editor may be open beside it.
#   pwsh run_voices_v64.ps1            # log: voices_v64.log next to this file
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$jev = 'D:\Program\anaconda3\envs\jev\python.exe'
$venv = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
$log = Join-Path $PSScriptRoot 'voices_v64.log'
function Step($name, [scriptblock]$what) {
    $t = Get-Date
    $out = & $what 2>&1 | Out-String
    "{0:HH:mm:ss}  {1,-22} {2,5:n0} s  {3}" -f (Get-Date), $name, ((Get-Date) - $t).TotalSeconds, ($out.Trim() -split "`n" | Select-Object -Last 1) | Tee-Object -FilePath $log -Append
}
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
"{0:HH:mm:ss}  start" -f (Get-Date) | Tee-Object -FilePath $log -Append
Step 'export seeds' { & $jev export_v64.py seeds }
Step 'export lines' { & $jev export_v64.py lines }
Step 'windows seeds' { pwsh -NoProfile -File synth_windows_v64.ps1 seeds }
Step 'windows lines' { pwsh -NoProfile -File synth_windows_v64.ps1 lines }
Step 'piper/kokoro seeds' { & $venv synth_v64.py seeds }
Step 'piper/kokoro lines' { & $venv synth_v64.py lines }
$env:STT_THREADS = '4'
foreach ($c in 'seedclean', 'seedkokoro', 'seedkokorox', 'seedvctkA') {
    $env:STT_LINES = 'seeds_v64.json'
    Step "stt $c" { & $venv run_stt.py parakeet-0.6b-v2 $c --tag _v64 }
}
foreach ($c in 'clean', 'kokoro', 'kokorox', 'vctkA', 'vctkB') {
    $env:STT_LINES = 'lines_v64.json'
    Step "stt $c" { & $venv run_stt.py parakeet-0.6b-v2 $c --tag _v64 }
}
"{0:HH:mm:ss}  done" -f (Get-Date) | Tee-Object -FilePath $log -Append
