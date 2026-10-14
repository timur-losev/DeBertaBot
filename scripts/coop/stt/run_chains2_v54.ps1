# Rounds two and three of the chains study (chains2_v54.py, router_v54.py, voice_chains.py, gguf_v54.py), all of it in
# order, one training on the GPU at a time. Logs next to this file. On the RTX 4090 and the i9-10900K round two with one
# seed takes about an hour and a quarter, everything with three seeds about seven hours.
#   pwsh run_chains2_v54.ps1                    round two, seed 0
#   pwsh run_chains2_v54.ps1 -From train        its voices, check and routers are done: the two decoders and the tables
#   pwsh run_chains2_v54.ps1 -From round3       round two is done: more voices, round three, the fold's own teachers,
#                                               the decoder as GGUF in llama.cpp
#   -Seeds 0,1,2                                every decoder with three seeds
# Before it: run_qlora_v54.ps1 (the first round's files are read here), the speech tools' environment in venv\
# (requirements.txt), llama.cpp under models\llama.cpp (gguf_v54.py says what), and in chains2\ the lines written and
# read by blind AI authors: teacher_a.json, teacher_b.json, ctx_teacher.json (training), blind_author.json with
# blind_ann1.json and blind_ann2.json, ctx_blind_author.json with ctx_blind_ann1.json and ctx_blind_ann2.json,
# held_ann1.json and held_ann2.json (frozen.txt has the hashes).
param([ValidateSet('voice', 'train', 'round3')]$From = 'voice', [int[]]$Seeds = @(0))
$py = 'D:\Program\anaconda3\envs\jev\python.exe'
$voice = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not $env:HF_HUB_OFFLINE) { $env:HF_HUB_OFFLINE = '1' }
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $PSScriptRoot
$t0 = Get-Date
function Step($exe, $log, $cmd) {
    & $exe @cmd > $log 2> "$log.err"
    "{0,6:n0} s  {1} (exit {2})" -f ((Get-Date) - $t0).TotalSeconds, ($cmd -join ' '), $LASTEXITCODE
}
if ($From -eq 'voice') {
    # what Parakeet hears: the teacher's r6 and cs lines from the training voices, the blind lines from unseen ones (CPU, idle priority)
    Step $voice 'chains2_54_voice.log' @('voice_chains.py', 'train', 'chains\teacher_heard.json', 'chains\teacher_lines.json')
    Step $voice 'chains2_54_voice.log' @('voice_chains.py', 'train', 'chains2\teacher_heard.json', 'chains2\teacher_a.json', 'chains2\teacher_b.json')
    Step $voice 'chains2_54_voice.log' @('voice_chains.py', 'test', 'chains\blind_heard.json', 'chains\blind_author.json')
    Step $voice 'chains2_54_voice.log' @('voice_chains.py', 'test', 'chains2\blind_heard.json', 'chains2\blind_author.json')
    Step $py 'chains2_54_check.log' @('chains2_v54.py', 'check')
    foreach ($size in 'small', 'base') { Step $py "router54_train_r2_$size.log" @('router_v54.py', 'train', 'r2', $size, '0') }
}
if ($From -ne 'round3') {
    foreach ($seed in $Seeds) { foreach ($variant in 'names', 'pieces') { Step $py "chains2_54_train_${variant}_$seed.log" @('chains2_v54.py', 'train', $variant, $seed) } }
} else {
    # three unseen speakers a line for the tests, two more training voices for the teacher's lines, the context items as heard
    Step $voice 'chains3_54_voice.log' @('voice_chains.py', 'test3', 'chains2\blind_heard.json', 'chains2\blind_author.json')
    Step $voice 'chains3_54_voice.log' @('voice_chains.py', 'test3', 'chains2\ctx_blind_heard.json', 'chains2\ctx_blind_author.json')
    Step $voice 'chains3_54_voice.log' @('voice_chains.py', 'test3', 'chains\blind_heard.json', 'chains\blind_author.json')
    Step $voice 'chains3_54_voice.log' @('voice_chains.py', 'train', 'chains2\ctx_teacher_heard.json', 'chains2\ctx_teacher.json')
    Step $voice 'chains3_54_voice.log' @('voice_chains.py', 'train2', 'chains\teacher_heard.json', 'chains\teacher_lines.json')
    Step $voice 'chains3_54_voice.log' @('voice_chains.py', 'train2', 'chains2\teacher_heard.json', 'chains2\teacher_a.json', 'chains2\teacher_b.json')
    Step $voice 'chains3_54_voice.log' @('voice_chains.py', 'train2', 'chains2\ctx_teacher_heard.json', 'chains2\ctx_teacher.json')
    # the fold's own teachers, to read what a decoder makes of a held-out line
    foreach ($s in 0, 1, 2) { Step $py "chains2_54_fold0_$s.log" @('chains2_v54.py', 'fold0', $s) }
    # the round-two decoders answer the new tests; the round-two router sees them
    Step $py 'router54_train_r2_small.log' @('router_v54.py', 'train', 'r2', 'small', '0')
    foreach ($seed in $Seeds) { foreach ($variant in 'names', 'pieces') { Step $py "chains2_54_answer_${variant}_$seed.log" @('chains2_v54.py', 'answer', $variant, $seed) } }
    foreach ($seed in $Seeds) { foreach ($variant in 'names3', 'pieces3') { Step $py "chains2_54_train_${variant}_$seed.log" @('chains2_v54.py', 'train', $variant, $seed) } }
    Step $py 'router54_train_r3_small.log' @('router_v54.py', 'train', 'r3', 'small', '0')
    # the rewriter as a game would run it: the GPU, then the CPU alone
    Step $py 'gguf54_make_pieces3_0.log' @('gguf_v54.py', 'make', 'pieces3', '0')
    foreach ($backend in 'vulkan', 'cpu8', 'cpu4') { Step $py "gguf54_bench_pieces3_0_$backend.log" @('gguf_v54.py', 'bench', 'pieces3', '0', $backend) }
    Step $py 'gguf54_score.log' @('gguf_v54.py', 'score')
}
Step $py 'chains2_54_read.log' @('chains2_v54.py', 'read')
Step $py 'router54_score.log' @('router_v54.py', 'score')
Step $py 'chains2_54_score.log' @('chains2_v54.py', 'score')
