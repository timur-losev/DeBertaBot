# The bot's brain as one folder a game starts `coop_cli --serve` from: the exe with its two DLLs, a bot's cpp/
# directory (config, vocabulary, ONNX members) and the speech recognizer's model. A copy, so that a running game
# does not hold the build directory's exe open, and so that the game project needs nothing from this repository.
#
#   pwsh deploy_brain.ps1 -Target J:\UE4\Projects\LyraStarterGame58\Binaries\CoopBrain            # bot v54
#   pwsh deploy_brain.ps1 -Target D:\Game\Binaries\CoopBrain -Bot coop-deberta-v3-ens3-v53 -Build <build dir>\Release
#   pwsh deploy_brain.ps1 -Target D:\Game\Binaries\CoopBrain -Chain coop-chain-v54     # with the router and the decoder
#   pwsh deploy_brain.ps1 -Target ...\CoopBrainV6 -Bot coop-deberta-v3-ens3-v61 -Decider <export_game.py folder>
#                    # with the optional second reader: <Target>\decider\ decider.json, decider.gguf (1.9 GB), decider_tests.json
#   pwsh deploy_brain.ps1 -Target ...\CoopBrainV6 -Bot coop-deberta-v3-ens3-v61 -Chain coop-chain-v62 `
#        -SttMulti <stt>\models\sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8
#                    # Russian and Spanish players: chain v62 (three languages in, English orders out) and <Target>\stt_v3
#
# Layout written:  <Target>\coop_cli.exe, onnxruntime.dll, sherpa-onnx-c-api.dll
#                  <Target>\bot\      intent_config.json, vocab.tsv, model*.onnx
#                  <Target>\stt\      encoder.int8.onnx, decoder.int8.onnx, joiner.int8.onnx, tokens.txt
#                  <Target>\deployed.json   what was copied, from where, when
# with -Chain (rewriter.h; the game then starts the service with `--chain <Target>\chain`):
#                  <Target>\llama.dll, ggml*.dll, libomp.dll      llama.cpp, from a build that found it (setup_llama.ps1)
#                  <Target>\chain\    chain_config.json, router.onnx, decoder.gguf (1 GB)
# the bot's voice (voice.h; the game then starts the service with `--tts-piper <Target>\voice`), when -Voice is there:
#                  <Target>\voice\    <name>.onnx, <name>.onnx.json, tokens.txt, espeak-ng-data\, MODEL_CARD (90 MB)
# the bot's lines in the player's language (localize.h; the game starts the service with `--replies <Target>\replies\
# replies_<lang>.json --voice-local <Target>\voice_<lang>` for a Russian or Spanish player), from -Replies and -LocalVoices:
#                  <Target>\replies\  replies_ru.json, replies_es.json
#                  <Target>\voice_<name>\  a Piper or Kokoro export and voice.json ({"speaker", "lang"})
#   pwsh deploy_brain.ps1 -Target ...\CoopBrainV6 -Bot coop-deberta-v3-ens3-v61 -Chain coop-chain-v63 `
#        -LocalVoices 'ru=<tts>\vits-piper-ru_RU-denis-medium', 'es=<tts>\vits-piper-es_MX-ald-medium', 'es_kokoro=<tts>\kokoro-multi-lang-v1_0@53'
param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$Bot = 'coop-deberta-v3-ens3-v54',
    [string]$Build = (Join-Path $PSScriptRoot '..\build\Release'),
    [string]$Stt = (Join-Path $PSScriptRoot '..\..\..\scripts\coop\stt\models\sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8'),
    [string]$Chain = '',
    # a decider folder (scripts/coop/decider/export_game.py): the optional second reader; '' keeps whatever is there
    [string]$Decider = '',
    # the speech recognizer for Russian and Spanish players (Parakeet TDT 0.6B v3, 25 languages) -> <Target>\stt_v3; the
    # game starts the brain with it when its language is ru or es. '' keeps whatever is there
    [string]$SttMulti = '',
    # a sherpa-onnx Piper export; '' leaves the voice out (the game falls back to the system's voice)
    [string]$Voice = (Join-Path $PSScriptRoot '..\..\..\scripts\coop\stt\tts\vits-piper-en_GB-vctk-medium'),
    # the reply tables (scripts/coop/replies/replies_<lang>.json); '' leaves <Target>\replies as it is
    [string]$Replies = (Join-Path $PSScriptRoot '..\..\..\scripts\coop\replies'),
    # the players' languages' voices: name=folder[@speaker] ("ru=...\vits-piper-ru_RU-denis-medium", "es_kokoro=...\kokoro-multi-lang-v1_0@53");
    # the name's first two letters are the voice's language. Each goes to <Target>\voice_<name>; none given keeps what is there
    [string[]]$LocalVoices = @()
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$botDir = Join-Path $repo "models\$Bot\cpp"
$Build = (Resolve-Path $Build).Path
$Stt = (Resolve-Path $Stt).Path
foreach ($need in "$Build\coop_cli.exe", "$Build\onnxruntime.dll", "$Build\sherpa-onnx-c-api.dll", "$botDir\intent_config.json", "$botDir\vocab.tsv", "$Stt\tokens.txt") {
    if (-not (Test-Path $need)) { throw "missing: $need" }
}
$members = (Get-Content "$botDir\intent_config.json" -Raw | ConvertFrom-Json).members
New-Item -ItemType Directory -Force "$Target\bot", "$Target\stt" | Out-Null
Copy-Item "$Build\coop_cli.exe", "$Build\onnxruntime.dll", "$Build\sherpa-onnx-c-api.dll" $Target -Force
Copy-Item "$botDir\intent_config.json", "$botDir\vocab.tsv" "$Target\bot" -Force
Get-ChildItem "$Target\bot" -Filter '*.onnx' | Where-Object { $members -notcontains $_.Name } | Remove-Item -Force   # another bot's members
foreach ($f in $members) { Copy-Item "$botDir\$f" "$Target\bot" -Force }
foreach ($f in 'encoder.int8.onnx', 'decoder.int8.onnx', 'joiner.int8.onnx', 'tokens.txt') { Copy-Item "$Stt\$f" "$Target\stt" -Force }
# llama.cpp's DLLs go with the exe whenever its build found llama.cpp: the exe links them, chain or no chain (a brain
# deployed without -Chain, e.g. the v6x one, otherwise ends at once with STATUS_DLL_NOT_FOUND, 0xC0000135)
if (Test-Path "$Build\llama.dll") {
    Get-ChildItem $Build -File | Where-Object { $_.Name -like 'llama.dll' -or $_.Name -like 'ggml*.dll' -or $_.Name -eq 'libomp.dll' } |
        Copy-Item -Destination $Target -Force
}
$chainFrom = $null
if ($Chain) {
    $chainDir = Join-Path $repo "models\$Chain\cpp"
    $ccfg = Get-Content "$chainDir\chain_config.json" -Raw | ConvertFrom-Json
    $chainFiles = @('chain_config.json', $ccfg.decoder) + @($ccfg.router | Where-Object { $_ })
    foreach ($need in @("$Build\llama.dll") + ($chainFiles | ForEach-Object { "$chainDir\$_" })) {
        if (-not (Test-Path $need)) { throw "missing: $need" }
    }
    New-Item -ItemType Directory -Force "$Target\chain" | Out-Null
    foreach ($f in $chainFiles) { Copy-Item "$chainDir\$f" "$Target\chain" -Force }
    $chainFrom = [ordered]@{ chain = $Chain; decoder = $ccfg.decoder_from; router = $ccfg.router_from; cut = $ccfg.cut }
}
$sttMultiFrom = $null
if ($SttMulti) {
    $SttMulti = (Resolve-Path $SttMulti).Path
    foreach ($need in 'encoder.int8.onnx', 'decoder.int8.onnx', 'joiner.int8.onnx', 'tokens.txt') {
        if (-not (Test-Path "$SttMulti\$need")) { throw "missing: $SttMulti\$need" }
    }
    New-Item -ItemType Directory -Force "$Target\stt_v3" | Out-Null
    foreach ($f in 'encoder.int8.onnx', 'decoder.int8.onnx', 'joiner.int8.onnx', 'tokens.txt') { Copy-Item "$SttMulti\$f" "$Target\stt_v3" -Force }
    $sttMultiFrom = Split-Path $SttMulti -Leaf
} elseif (Test-Path "$Target\stt_v3\tokens.txt") {
    $sttMultiFrom = 'kept from an earlier deploy'
}
$deciderFrom = $null
if ($Decider) {
    # the optional second reader of a line (coop_cli --decider): scripts/coop/decider/export_game.py's folder. The game
    # starts it only when asked (UOVCoopBotSettings::DeciderMode, ov.CoopBot.Brain.Decider)
    $Decider = (Resolve-Path $Decider).Path
    $dcfg = Get-Content "$Decider\decider.json" -Raw | ConvertFrom-Json
    foreach ($need in @("$Build\llama.dll", "$Decider\$($dcfg.model)")) { if (-not (Test-Path $need)) { throw "missing: $need" } }
    if (Test-Path "$Target\decider") { Remove-Item "$Target\decider" -Recurse -Force }
    New-Item -ItemType Directory -Force "$Target\decider" | Out-Null
    Copy-Item "$Decider\decider.json", "$Decider\$($dcfg.model)" "$Target\decider" -Force
    if (Test-Path "$Decider\decider_tests.json") { Copy-Item "$Decider\decider_tests.json" "$Target\decider" -Force }
    $deciderFrom = $dcfg.source
} elseif (Test-Path "$Target\decider\decider.json") {
    $deciderFrom = (Get-Content "$Target\decider\decider.json" -Raw | ConvertFrom-Json).source + ' (kept from an earlier deploy)'
}
$voiceFrom = $null
if ($Voice -and (Test-Path $Voice)) {
    $Voice = (Resolve-Path $Voice).Path
    $model = Get-ChildItem $Voice -Filter '*.onnx' | Select-Object -First 1
    foreach ($need in @($model.FullName, "$($model.FullName).json", "$Voice\tokens.txt", "$Voice\espeak-ng-data")) {
        if (-not $need -or -not (Test-Path $need)) { throw "missing: $need" }
    }
    if (Test-Path "$Target\voice") { Remove-Item "$Target\voice" -Recurse -Force }   # another voice's model
    New-Item -ItemType Directory -Force "$Target\voice" | Out-Null
    Copy-Item $model.FullName, "$($model.FullName).json", "$Voice\tokens.txt" "$Target\voice" -Force
    Copy-Item "$Voice\espeak-ng-data" "$Target\voice" -Recurse -Force
    if (Test-Path "$Voice\MODEL_CARD") { Copy-Item "$Voice\MODEL_CARD" "$Target\voice" -Force }   # the voice's data and its licence
    $voiceFrom = $model.BaseName
} elseif ($Voice) {
    "no voice at ${Voice}: the game will use the system's voice"
}
$repliesFrom = $null
if ($Replies -and (Test-Path $Replies)) {
    $tables = Get-ChildItem $Replies -Filter 'replies_*.json'
    if ($tables) {
        New-Item -ItemType Directory -Force "$Target\replies" | Out-Null
        $tables | Copy-Item -Destination "$Target\replies" -Force
        $repliesFrom = ($tables | ForEach-Object { $_.BaseName -replace '^replies_', '' }) -join ', '
    }
}
$localFrom = [ordered]@{}
foreach ($spec in $LocalVoices) {
    if ($spec -notmatch '^([a-z]{2}[a-z_]*)=(.+?)(@(\w+))?$') { throw "-LocalVoices: name=folder[@speaker], not $spec" }
    $name = $Matches[1]; $from = (Resolve-Path $Matches[2]).Path; $speaker = $Matches[4]
    $dest = "$Target\voice_$name"
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    New-Item -ItemType Directory -Force $dest | Out-Null
    if (Test-Path "$from\voices.bin") {   # Kokoro: the model, its voices and what its phonemes need; not its Chinese lexicons
        Copy-Item "$from\model.onnx", "$from\voices.bin", "$from\tokens.txt" $dest -Force
    } else {
        $model = Get-ChildItem $from -Filter '*.onnx' | Select-Object -First 1
        Copy-Item $model.FullName, "$($model.FullName).json", "$from\tokens.txt" $dest -Force
    }
    Copy-Item "$from\espeak-ng-data" $dest -Recurse -Force
    foreach ($card in 'MODEL_CARD', 'LICENSE') { if (Test-Path "$from\$card") { Copy-Item "$from\$card" $dest -Force } }
    [ordered]@{ speaker = $(if ($speaker) { $speaker } else { '' }); lang = $name.Substring(0, 2); from = (Split-Path $from -Leaf) } |
        ConvertTo-Json | Set-Content "$dest\voice.json" -Encoding UTF8
    $localFrom[$name] = (Split-Path $from -Leaf) + $(if ($speaker) { "@$speaker" } else { '' })
}
foreach ($d in Get-ChildItem $Target -Directory -Filter 'voice_*') {
    $n = $d.Name.Substring(6)
    if (-not $localFrom.Contains($n) -and (Test-Path "$($d.FullName)\voice.json")) { $localFrom[$n] = (Get-Content "$($d.FullName)\voice.json" -Raw | ConvertFrom-Json).from + ' (kept)' }
}
$cfg = Get-Content "$botDir\intent_config.json" -Raw | ConvertFrom-Json
# the long-term memory (coop_cli --memory, a build that found Wick): the game passes --memory only to a brain whose
# deployed.json says it has one, so that an older exe is never started with a flag it does not know
$probe = Join-Path ([IO.Path]::GetTempPath()) "coop_memory_probe_$PID"
& "$Target\coop_cli.exe" --memory-dump "$probe\probe.mv2s" *> $null
$memory = $LASTEXITCODE -eq 0
Remove-Item $probe -Recurse -Force -ErrorAction SilentlyContinue
[ordered]@{ bot = $Bot; labels = $cfg.labels.Count; gate = $cfg.gate; threshold = $cfg.threshold; members = $members; chain = $chainFrom; voice = $voiceFrom
            decider = $deciderFrom; stt_multilingual = $sttMultiFrom; replies = $repliesFrom; local_voices = $localFrom; memory = $memory
            exe_built = (Get-Item "$Build\coop_cli.exe").LastWriteTime.ToString('s'); from = $repo; deployed = (Get-Date).ToString('s') } |
    ConvertTo-Json | Set-Content "$Target\deployed.json" -Encoding UTF8
"deployed {0} ({1} labels, {2} gate, threshold {3}) to {4}: {5:n1} GB" -f $Bot, $cfg.labels.Count, $cfg.gate, $cfg.threshold, $Target,
    ((Get-ChildItem $Target -Recurse -File | Measure-Object Length -Sum).Sum / 1GB)
