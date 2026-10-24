# Fine-tunes a Piper medium voice on a rendered corpus (make_dataset.py) from the ru denis checkpoint, then exports it
# for the game's brain. Detached, logs next to the run:
#   pwsh train_voice.ps1 -Name brat_qw_central -Wavs work\brat\wav_qw_central -Csv work\brat\qw_central.csv -Epochs 400
# The denis checkpoint (rhasspy/piper-checkpoints, CC0 data) is first cleaned to its weights (clean_ckpt.py): it was
# saved on Linux, and its hyperparameters hold Linux paths that do not unpickle on Windows.
param(
    [Parameter(Mandatory)] [string]$Name,
    [Parameter(Mandatory)] [string]$Wavs,
    [Parameter(Mandatory)] [string]$Csv,
    [int]$Epochs = 400,
    [int]$Batch = 32
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$work = Join-Path $here 'work'
$py = Join-Path $work 'venv_piper\Scripts\python.exe'
$run = Join-Path $work "train_$Name"
New-Item -ItemType Directory -Force $run | Out-Null
$env:PYTHONUTF8 = '1'
Set-Location $run
& $py -m piper.train fit `
    --data.voice_name $Name `
    --data.csv_path (Resolve-Path $Csv) `
    --data.audio_dir (Resolve-Path $Wavs) `
    --model.sample_rate 22050 `
    --data.espeak_voice ru `
    --data.cache_dir (Join-Path $run 'cache') `
    --data.config_path (Join-Path $run 'config.json') `
    --data.batch_size $Batch `
    --data.validation_split 0.02 `
    --data.num_test_examples 4 `
    --trainer.max_epochs $Epochs `
    --trainer.accelerator gpu `
    --trainer.devices 1 `
    --trainer.precision 32 `
    --model.warmstart_ckpt (Join-Path $work 'ckpt_denis\denis_weights.ckpt') `
    --model.mos_metric none
