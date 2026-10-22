# v61's accented audio (export_accent_v61.py): the lines and seed commands read by the Windows voices of other languages
# (Russian, German). Each row names its voice and speaking rate; 16 kHz, 16-bit, mono. A file that is already there is
# kept, so a run that was cut short goes on. Windows only (System.Speech); needs the voices "Microsoft Irina",
# "Microsoft Pavel", "Microsoft Hedda", "Microsoft Katja", "Microsoft Stefan". Run in PowerShell 7:
#   pwsh synth_accent_v61.ps1 ru        # accent_ru_v61.json -> wav_ru (also: de, seedru, seedde)
param([Parameter(Mandatory)][ValidateSet('ru', 'de', 'seedru', 'seedde')][string]$Set)
Add-Type -AssemblyName System.Speech
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$rows = Get-Content (Join-Path $PSScriptRoot "accent_${Set}_v61.json") -Raw -Encoding utf8 | ConvertFrom-Json
$out = Join-Path $PSScriptRoot "wav_$Set"
New-Item -ItemType Directory -Force $out | Out-Null
$syn = New-Object System.Speech.Synthesis.SpeechSynthesizer
$made = 0
foreach ($r in $rows) {
    $wav = Join-Path $out $r.wav
    if (Test-Path $wav) { continue }
    $syn.SelectVoice($r.voice)
    $syn.Rate = [int]$r.rate
    $syn.SetOutputToWaveFile($wav, $fmt)
    $syn.Speak([string]$r.text)
    $made++
}
$syn.SetOutputToNull()
$syn.Dispose()
"wav_{0}: {1} new files ({2} rows)" -f $Set, $made, $rows.Count
