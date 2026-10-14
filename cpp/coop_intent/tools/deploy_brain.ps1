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
param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$Bot = 'coop-deberta-v3-ens3-v54',
    [string]$Build = (Join-Path $PSScriptRoot '..\build\Release'),
    [string]$Stt = (Join-Path $PSScriptRoot '..\..\..\scripts\coop\stt\models\sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8'),
    [string]$Chain = ''
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
$chainFrom = $null
if ($Chain) {
    $chainDir = Join-Path $repo "models\$Chain\cpp"
    $ccfg = Get-Content "$chainDir\chain_config.json" -Raw | ConvertFrom-Json
    $chainFiles = @('chain_config.json', $ccfg.decoder) + @($ccfg.router | Where-Object { $_ })
    foreach ($need in @("$Build\llama.dll") + ($chainFiles | ForEach-Object { "$chainDir\$_" })) {
        if (-not (Test-Path $need)) { throw "missing: $need" }
    }
    New-Item -ItemType Directory -Force "$Target\chain" | Out-Null
    Get-ChildItem $Build -File | Where-Object { $_.Name -like 'llama.dll' -or $_.Name -like 'ggml*.dll' -or $_.Name -eq 'libomp.dll' } |
        Copy-Item -Destination $Target -Force
    foreach ($f in $chainFiles) { Copy-Item "$chainDir\$f" "$Target\chain" -Force }
    $chainFrom = [ordered]@{ chain = $Chain; decoder = $ccfg.decoder_from; router = $ccfg.router_from; cut = $ccfg.cut }
}
$cfg = Get-Content "$botDir\intent_config.json" -Raw | ConvertFrom-Json
[ordered]@{ bot = $Bot; labels = $cfg.labels.Count; gate = $cfg.gate; threshold = $cfg.threshold; members = $members; chain = $chainFrom
            exe_built = (Get-Item "$Build\coop_cli.exe").LastWriteTime.ToString('s'); from = $repo; deployed = (Get-Date).ToString('s') } |
    ConvertTo-Json | Set-Content "$Target\deployed.json" -Encoding UTF8
"deployed {0} ({1} labels, {2} gate, threshold {3}) to {4}: {5:n1} GB" -f $Bot, $cfg.labels.Count, $cfg.gate, $cfg.threshold, $Target,
    ((Get-ChildItem $Target -Recurse -File | Measure-Object Length -Sum).Sum / 1GB)
