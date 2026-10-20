# The bot's brain as one folder a game starts `coop_cli --serve` from: the exe with its two DLLs, a bot's cpp/
# directory (config, vocabulary, ONNX members) and the speech recognizer's model. A copy, so that a running game
# does not hold the build directory's exe open, and so that the game project needs nothing from this repository.
#
#   pwsh deploy_brain.ps1 -Target J:\UE4\Projects\LyraStarterGame58\Binaries\CoopBrain            # bot v54
#   pwsh deploy_brain.ps1 -Target D:\Game\Binaries\CoopBrain -Bot coop-deberta-v3-ens3-v53 -Build <build dir>\Release
#   pwsh deploy_brain.ps1 -Target D:\Game\Binaries\CoopBrain -Chain coop-chain-v54     # with the router and the decoder
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
param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$Bot = 'coop-deberta-v3-ens3-v54',
    [string]$Build = (Join-Path $PSScriptRoot '..\build\Release'),
    [string]$Stt = (Join-Path $PSScriptRoot '..\..\..\scripts\coop\stt\models\sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8'),
    [string]$Chain = '',
    # a sherpa-onnx Piper export; '' leaves the voice out (the game falls back to the system's voice)
    [string]$Voice = (Join-Path $PSScriptRoot '..\..\..\scripts\coop\stt\tts\vits-piper-en_GB-vctk-medium')
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
$cfg = Get-Content "$botDir\intent_config.json" -Raw | ConvertFrom-Json
[ordered]@{ bot = $Bot; labels = $cfg.labels.Count; gate = $cfg.gate; threshold = $cfg.threshold; members = $members; chain = $chainFrom; voice = $voiceFrom
            exe_built = (Get-Item "$Build\coop_cli.exe").LastWriteTime.ToString('s'); from = $repo; deployed = (Get-Date).ToString('s') } |
    ConvertTo-Json | Set-Content "$Target\deployed.json" -Encoding UTF8
"deployed {0} ({1} labels, {2} gate, threshold {3}) to {4}: {5:n1} GB" -f $Bot, $cfg.labels.Count, $cfg.gate, $cfg.threshold, $Target,
    ((Get-ChildItem $Target -Recurse -File | Measure-Object Length -Sum).Sum / 1GB)
