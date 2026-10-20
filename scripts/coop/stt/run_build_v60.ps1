# Bot v60, all of its training (Windows, RTX 4090): three out-of-fold runs (five trainings each: the gate and the threshold,
# ensemble_bot_v60.py) and three final models. At most three processes at a time on the GPU (about 4.5 GB of VRAM each), so
# that an editor left open beside it keeps its share. Logs: build_v60_<mode>_<seed>.log next to this file.
#   pwsh run_build_v60.ps1           # PowerShell 7; the torch environment's python is $py below (README.md)
param([int]$Parallel = 3)
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$env:HF_HUB_OFFLINE = '1'
# one string per job: PowerShell flattens a list of two-element lists once it is down to one of them
$queue = [System.Collections.Generic.Queue[string]]::new([string[]]@('oof 0', 'oof 1', 'oof 2', 'final 0', 'final 1', 'final 2'))
$running = @()
$t0 = Get-Date
while ($queue.Count -or $running.Count) {
    $running = @($running | Where-Object { -not $_.HasExited })
    while ($queue.Count -and $running.Count -lt $Parallel) {
        $mode, $seed = $queue.Dequeue() -split ' '
        $log = Join-Path $PSScriptRoot "build_v60_${mode}_${seed}.log"
        $running += Start-Process -FilePath $py -ArgumentList @('build_v60.py', $mode, $seed) -WorkingDirectory $PSScriptRoot `
            -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
        "{0:HH:mm:ss}  started $mode $seed" -f (Get-Date)
    }
    Start-Sleep -Seconds 5
}
"all six processes finished in {0:n0} s" -f ((Get-Date) - $t0).TotalSeconds
Get-ChildItem $PSScriptRoot -Filter 'build_v60_*.log' | ForEach-Object { "{0}: {1}" -f $_.Name, (Get-Content $_.FullName -Tail 1) }
