# The Windows voices' share of the test audio: wav_clean (the 422 lines of lines.json) and wav_seedclean (the 580 seed
# commands of seeds.json). Each row of the list names its voice; 16 kHz, 16-bit, mono, speaking rate 1.
# Windows only (System.Speech); needs the English voices "Microsoft David Desktop", "Microsoft Zira Desktop" and
# "Microsoft Mark". Run in PowerShell 7:   pwsh synth_windows.ps1
Add-Type -AssemblyName System.Speech
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
foreach ($set in @(@('lines.json', 'wav_clean'), @('seeds.json', 'wav_seedclean'))) {
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
    "{0}: {1} files" -f $set[1], (Get-ChildItem $out -Filter *.wav).Count
}
