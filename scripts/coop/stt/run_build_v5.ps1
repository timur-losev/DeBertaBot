# Bot v5, all of its training: three out-of-fold runs (five trainings each: the gate and the threshold) and three final
# models, at most four processes at a time on one GPU (about 4.5 GB of VRAM each). Then score_v5.py reads the results
# and writes bot_config.json. Logs: build_v5_<mode>_<seed>.log next to this file.
#   pwsh run_build_v5.ps1            # PowerShell 7; the torch environment's python is $py below (README.md)
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$env:HF_HUB_OFFLINE = '1'
$queue = @(@('oof', 0), @('oof', 1), @('oof', 2), @('final', 0), @('final', 1), @('final', 2))
$running = @()
$t0 = Get-Date
while ($queue.Count -or $running.Count) {
    $running = @($running | Where-Object { -not $_.HasExited })
    while ($queue.Count -and $running.Count -lt 4) {
        $mode, $seed = $queue[0]
        $queue = @($queue | Select-Object -Skip 1)
        $log = Join-Path $PSScriptRoot "build_v5_${mode}_${seed}.log"
        $running += Start-Process -FilePath $py -ArgumentList @('build_v5.py', $mode, $seed) -WorkingDirectory $PSScriptRoot `
            -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
        "started $mode $seed"
    }
    Start-Sleep -Seconds 5
}
"all six processes finished in {0:n0} s" -f ((Get-Date) - $t0).TotalSeconds
Get-ChildItem $PSScriptRoot -Filter 'build_v5_*.log' | ForEach-Object { Get-Content $_.FullName -Tail 1 }
