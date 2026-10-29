# Frees the GPU without losing training progress: every running training with snapshots -- the decoder (chainsNN_vNN.py
# train) and the classifier (build_vNN.py oof|final) -- gets a STOP file in its *_snapshot folder under models/, takes a
# snapshot at its next step and exits; the classifier's runner (run_build_vNN.ps1) starts no new job. This waits for that.
# To go on later: run the same scripts again (run_chains11_v67.ps1, run_build_v67.ps1).
#   pwsh stop_training.ps1
$models = Join-Path $PSScriptRoot '..\..\..\models'
$pattern = 'chains\d+_v\d+\.py train|build_v\d+\.py (oof|final)'
$running = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match $pattern }
if (-not $running) { 'no training is running'; exit 0 }
New-Item -ItemType File -Path (Join-Path $PSScriptRoot 'STOP_TRAINING') -Force | Out-Null   # the runners: no new job
$dirs = Get-ChildItem $models -Recurse -Directory -Filter '*_snapshot' -ErrorAction SilentlyContinue
foreach ($d in $dirs) { New-Item -ItemType File -Path (Join-Path $d.FullName 'STOP') -Force | Out-Null }
"asked {0} training(s) to stop" -f @($running).Count
$deadline = (Get-Date).AddMinutes(5)
while ((Get-Date) -lt $deadline) {
    $left = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match $pattern }
    if (-not $left) { 'stopped, snapshots saved; the GPU is free'; exit 0 }
    Start-Sleep -Seconds 2
}
'still running after 5 minutes (a training still loading its data does not see the stop yet): run this again'
exit 1
