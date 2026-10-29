# Everything round v67 trains, for one night (the owner, 2026-10-28): the classifier (run_build_v67.ps1, in its own process)
# and beside it the two decoders one after the other, the short system turn first (about 1.5 h), then the long one (about 7 h).
# Log run_v67_all.log next to this file. Stop without losing anything: pwsh stop_training.ps1 (nothing new starts after it).
# Run this again to go on: a decoder with its gguf made is skipped, a stopped one goes on from its snapshot; the classifier's
# runner skips its finished jobs.
#   pwsh run_v67_all.ps1
Set-Location $PSScriptRoot
$log = Join-Path $PSScriptRoot 'run_v67_all.log'
function Say($text) { "{0:yyyy-MM-dd HH:mm:ss}  $text" -f (Get-Date) | Tee-Object -FilePath $log -Append }
$gguf = Join-Path $PSScriptRoot 'models\gguf'
$marker = Join-Path $PSScriptRoot 'STOP_TRAINING'
Remove-Item $marker -ErrorAction SilentlyContinue      # a stop asked of an earlier run, not of this one
$build = Start-Process pwsh -ArgumentList @('-NoProfile', '-File', (Join-Path $PSScriptRoot 'run_build_v67.ps1')) -WorkingDirectory $PSScriptRoot `
    -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'build_v67_runner.log') -RedirectStandardError (Join-Path $PSScriptRoot 'build_v67_runner.log.err')
$null = $build.Handle                                    # without it ExitCode stays empty after WaitForExit
Say "classifier started (run_build_v67.ps1, pid $($build.Id))"
foreach ($d in @(@{ Name = 'short'; Variant = 'pieces12v67s_final'; Args = @('-Short') }, @{ Name = 'long'; Variant = 'pieces12v67_final'; Args = @() })) {
    if (Test-Path (Join-Path $gguf "$($d.Variant)_s0-Q4_K_M.gguf")) { Say "decoder $($d.Name): done before, skipped"; continue }
    if (Test-Path $marker) { Say "stop asked: decoder $($d.Name) not started"; break }
    Say "decoder $($d.Name) started"
    & pwsh -NoProfile -File (Join-Path $PSScriptRoot 'run_chains11_v67.ps1') @($d.Args)
    $code = $LASTEXITCODE
    Say "decoder $($d.Name) ended (exit $code)"
    if ($code -ne 0) { break }        # 3: a stop asked; anything else: a failure, its log says which
}
$build.WaitForExit()
Say "classifier ended (exit $($build.ExitCode))"
