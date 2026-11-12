# Round v70's C++ checks (TODO_v70.md, acceptance): coop_cli against the Python bot for bot v70, the reply tables, and with
# -Chain the decoder's chain tests (CPU). One line per check in checks_v70.log, the whole output in checks_v70_<check>.out.
#   pwsh checks_v70.ps1            the bot's checks and the reply tables
#   pwsh checks_v70.ps1 -Chain     ... and chain v70's chain tests
#   pwsh checks_v70.ps1 -Bot coop-deberta-v3-ens3-v70c [-Chain]
param([switch]$Chain, [string]$Bot = 'coop-deberta-v3-ens3-v70', [string]$ChainName = 'coop-chain-v70')
$ErrorActionPreference = 'Continue'
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'BelowNormal'
$repo = 'G:\Proj\ollaya\DeBertaBot'
$exe = "$repo\cpp\coop_intent\build\Release\coop_cli.exe"
$bot = "$repo\models\$Bot\cpp"
$chainDir = "$repo\models\$ChainName\cpp"
$log = Join-Path $PSScriptRoot 'checks_v70.log'
"{0:HH:mm:ss}  checks: bot $bot, exe {1}" -f (Get-Date), (Get-FileHash $exe -Algorithm MD5).Hash.Substring(0, 8) | Out-File $log -Append -Encoding utf8
function Check([string]$name, [string[]]$a) {
    $out = Join-Path $PSScriptRoot "checks_v70_$name.out"
    & $exe @a *> $out
    $code = $LASTEXITCODE
    $last = (Get-Content $out -Tail 3 | Where-Object { $_.Trim() }) -join ' / '
    "{0:HH:mm:ss}  {1,-16} exit {2}: {3}" -f (Get-Date), $name, $code, $last | Out-File $log -Append -Encoding utf8
}
foreach ($t in 'golden', 'tokenizer-tests', 'location-tests', 'dialogue', 'gate-tests', 'decide-tests', 'world-tests', 'item-tests') {
    Check $t @('--model-dir', $bot, "--$t")
}
Check 'time-tests' @('--model-dir', $bot, '--time-tests', "$repo\scripts\coop\time_phrase_tests.jsonl")
Check 'teach-tests' @('--model-dir', $bot, '--teach-tests', "$repo\cpp\coop_intent\tools\teach_tests.json")
foreach ($t in 'ru', 'es', 'ru_brat', 'es_brat', 'en_brat') {
    Check "replies-$t" @('--model-dir', $bot, '--replies-check', "$repo\scripts\coop\replies\replies_$t.json")
}
if ($Chain) {
    Check 'chain-tests' @('--model-dir', $bot, '--chain', $chainDir, '--chain-tests', '--decoder-cpu')
}
"{0:HH:mm:ss}  done" -f (Get-Date) | Out-File $log -Append -Encoding utf8
