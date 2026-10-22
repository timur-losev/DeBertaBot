# The Windows voices' share of the audio v61 adds: seeds_v61.json -> wav_seedclean (the same folder as v4 to v60; the file
# names differ). v61 has no lines of its own. Each row of a list names its voice; 16 kHz, 16-bit, mono, speaking rate 1.
# Windows only (System.Speech); needs the English voices "Microsoft David Desktop", "Microsoft Zira Desktop" and
# "Microsoft Mark". Run in PowerShell 7:   pwsh synth_windows_v61.ps1 seeds
param([Parameter(Mandatory)][ValidateSet('seeds')][string]$Part)
Add-Type -AssemblyName System.Speech
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$sets = @{ seeds = @('seeds_v61.json', 'wav_seedclean') }
foreach ($set in @(,$sets[$Part])) {
    $rows = Get-Content (Join-Path $PSScriptRoot $set[0]) -Raw -Encoding utf8 | ConvertFrom-Json
    $out = Join-Path $PSScriptRoot $set[1]
    New-Item -ItemType Directory -Force $out | Out-Null
    $syn = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $syn.Rate = 1
    foreach ($r in $rows) {
        $syn.SelectVoice($r.voice)
        $syn.SetOutputToWaveFile((Join-Path $out $r.wav), $fmt)
        $syn.Speak([string]$r.text)
    }
    $syn.SetOutputToNull()
    $syn.Dispose()
    "{0}: {1} new files" -f $set[1], $rows.Count
}
