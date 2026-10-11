# After run_kd_v54.ps1 (it waits for its kd54_score.log): the nearest-neighbour study on the students' vectors, the
# xsmall and small students as bots (bot_config, export, test files, int8 variants), the v54 ensemble as a bot from the
# teachers' out-of-fold fit, and the C++ checks and the latency of each on the scratch exe (the in-place exe may be
# held open by the owner's chat). Logs: kd54_after.log next to this file.
#   pwsh after_kd_v54.ps1
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$env:HF_HUB_OFFLINE = '1'
$env:COOP_TAG = 'v54'
$exe = 'G:\Temp\claude\g--Proj-Qwen-2-5-1B-RLCD\aef82590-78c0-4e29-816f-2f4ec0f59a97\scratchpad\cpptest\build\Release\coop_cli.exe'
$repo = 'G:\Proj\ollaya\DeBertaBot'
$log = Join-Path $PSScriptRoot 'kd54_after.log'
Set-Location $PSScriptRoot
while (-not (Test-Path (Join-Path $PSScriptRoot 'kd54_score.log'))) { Start-Sleep -Seconds 60 }
Start-Sleep -Seconds 30
function Say($s) { $s | Tee-Object -FilePath $log -Append }
function Checks($dir, $modes) {
    foreach ($m in $modes) {
        & $exe --model-dir $dir $m --threads 1 2>&1 | Select-String '^(tokenizer tests|location tests|gate tests|decide tests|golden|dialogue,|world tests)' |
            ForEach-Object { Say ("  " + $_.Line.Substring(0, [Math]::Min(220, $_.Line.Length))) }
    }
}
function Bench($dir) {
    & $exe --model-dir $dir --bench --threads 1 2>&1 | Select-String 'median|p99|load|working set' | ForEach-Object { Say ("  " + $_.Line) }
}
Say "==== nearest neighbours"
foreach ($s in 'xsmall', 'small') { & $py knn_v54.py $s kd 0 2>&1 | Tee-Object -FilePath $log -Append }
Say "==== the v54 ensemble as a bot (threshold from the teachers' out-of-fold run)"
& $py ensemble_bot_v54.py 2>&1 | Tee-Object -FilePath $log -Append
$ens = "$repo\models\coop-deberta-v3-ens3-v54"
Checks "$ens\cpp" @('--tokenizer-tests', '--location-tests', '--gate-tests', '--decide-tests', '--golden', '--dialogue', '--world-tests')
Bench "$ens\cpp"
foreach ($s in 'xsmall', 'small') {
    Say "==== student $s as a bot"
    & $py student_bot_v54.py $s kd 0 2>&1 | Tee-Object -FilePath $log -Append
    $d = "$repo\models\coop-deberta-v3-$s-kd-v54"
    Checks "$d\cpp" @('--tokenizer-tests', '--location-tests', '--gate-tests', '--decide-tests', '--golden', '--dialogue', '--world-tests')
    Bench "$d\cpp"
    foreach ($v in 'int8_all', 'int8_per_channel', 'uint8_matmul_only') {
        Say "-- $s $v"
        & $exe --model-dir "$d\cpp_$v" --golden --threads 1 2>&1 | Select-String '^golden' | ForEach-Object { Say ("  " + $_.Line) }
        Bench "$d\cpp_$v"
    }
}
Say "==== owner lines and the probe"
Set-Location "$repo\scripts\coop"
foreach ($b in $ens, "$repo\models\coop-deberta-v3-xsmall-kd-v54", "$repo\models\coop-deberta-v3-small-kd-v54") {
    Say "-- $b"
    foreach ($f in 'owner_voice_20261009.json', 'owner_voice_20261009b.json', 'owner_voice_20261009c.json') {
        & $py owner_voice.py $b $f 2>&1 | Select-String '^\s+(ok|NO)|^coop-' | ForEach-Object { Say $_.Line }
    }
    & $py probe_v54.py $b 2>&1 | Select-String '^\s+(ok|NO)|^coop-' | ForEach-Object { Say $_.Line }
}
Say "==== done"
