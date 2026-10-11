# The distillation study (distill_v54.py), all of it, at most four training processes on the GPU at a time (the
# build_v54.py finals that may still be running count). Phases in order: the fold teachers (3 seeds), the students
# (every size and tag below), the final students on everything. Logs: kd54_<what>.log next to this file.
#   pwsh run_kd_v54.ps1
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$env:HF_HUB_OFFLINE = '1'
$t0 = Get-Date
function Busy { @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'build_v54\.py (final|oof)|distill_v54\.py (teachers|student|final)' }).Count }
function RunPhase($name, $jobs) {
    $queue = @($jobs)
    $running = @()
    while ($queue.Count -or $running.Count) {
        $running = @($running | Where-Object { -not $_.HasExited })
        while ($queue.Count -and (Busy) -lt 4) {
            $args = $queue[0]
            $queue = @($queue | Select-Object -Skip 1)
            $log = Join-Path $PSScriptRoot ("kd54_" + ($args -join '_') + ".log")
            $running += Start-Process -FilePath $py -ArgumentList (@('distill_v54.py') + $args) -WorkingDirectory $PSScriptRoot `
                -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
            "{0,6:n0} s  started {1}" -f ((Get-Date) - $t0).TotalSeconds, ($args -join ' ')
            Start-Sleep -Seconds 20
        }
        Start-Sleep -Seconds 10
    }
    "{0,6:n0} s  phase {1} done" -f ((Get-Date) - $t0).TotalSeconds, $name
}
RunPhase 'teachers' @(@('teachers', 0), @('teachers', 1), @('teachers', 2))
RunPhase 'students' @(
    @('student', 'xsmall', 0, 'kd'), @('student', 'small', 0, 'kd'), @('student', 'base', 0, 'kd'),
    @('student', 'xsmall', 0, 'hard'), @('student', 'small', 0, 'hard'),
    @('student', 'xsmall', 1, 'kd'), @('student', 'xsmall', 2, 'kd'), @('student', 'small', 1, 'kd'), @('student', 'small', 2, 'kd'),
    @('student', 'xsmall', 0, 'kd24'))
RunPhase 'finals' @(@('final', 'xsmall', 0, 'kd'), @('final', 'small', 0, 'kd'), @('final', 'base', 0, 'kd'))
& $py distill_v54.py score 2>&1 | Tee-Object -FilePath (Join-Path $PSScriptRoot 'kd54_score.log')
