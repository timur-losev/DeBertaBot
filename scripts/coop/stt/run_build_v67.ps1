# Bot v67, all of its training (Windows, RTX 4090): three out-of-fold runs (five trainings each: the gate and the threshold,
# ensemble_bot_v67.py) and three final models. At most three processes at a time on the GPU (about 4.5 GB of VRAM each), so
# that an editor left open beside it keeps its share. Logs: build_v67_<mode>_<seed>.log next to this file.
# Every training takes a snapshot every 30 minutes. pwsh stop_training.ps1 stops them all without losing anything (and this
# starts no new job); run this again to go on: a job that is done is skipped, a stopped one goes on from its snapshot.
#   pwsh run_build_v67.ps1           # PowerShell 7; the torch environment's python is $py below (README.md)
param([int]$Parallel = 3)
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$env:HF_HUB_OFFLINE = '1'
$marker = Join-Path $PSScriptRoot 'STOP_TRAINING'
Remove-Item $marker -ErrorAction SilentlyContinue   # a stop asked of an earlier run, not of this one
# one string per job: PowerShell flattens a list of two-element lists once it is down to one of them
$queue = [System.Collections.Generic.Queue[string]]::new([string[]]@('oof 0', 'oof 1', 'oof 2', 'final 0', 'final 1', 'final 2'))
$running = @()
$t0 = Get-Date
while ($queue.Count -or $running.Count) {
    $running = @($running | Where-Object { -not $_.HasExited })
    if ((Test-Path $marker) -and $queue.Count) {
        "{0:HH:mm:ss}  stop asked: no new job ({1} left for the next run)" -f (Get-Date), $queue.Count
        $queue.Clear()
    }
    while ($queue.Count -and $running.Count -lt $Parallel) {
        $mode, $seed = $queue.Dequeue() -split ' '
        $log = Join-Path $PSScriptRoot "build_v67_${mode}_${seed}.log"
        $running += Start-Process -FilePath $py -ArgumentList @('build_v67.py', $mode, $seed) -WorkingDirectory $PSScriptRoot `
            -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
        "{0:HH:mm:ss}  started $mode $seed" -f (Get-Date)
    }
    Start-Sleep -Seconds 5
}
if (Test-Path $marker) {
    Remove-Item $marker
    "stopped on request after {0:n0} s; run run_build_v67.ps1 again to go on" -f ((Get-Date) - $t0).TotalSeconds
    exit 3
}
"all six processes finished in {0:n0} s" -f ((Get-Date) - $t0).TotalSeconds
Get-ChildItem $PSScriptRoot -Filter 'build_v67_*.log' | ForEach-Object { "{0}: {1}" -f $_.Name, (Get-Content $_.FullName -Tail 1) }
