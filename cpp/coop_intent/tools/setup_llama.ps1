# llama.cpp for the engine's decoder (src/llama_rewriter.cpp), laid out like the other third-party runtimes:
#   third_party\llama.cpp-<BUILD>-win-x64\include   llama.h and the ggml headers it includes (from the source archive)
#   third_party\llama.cpp-<BUILD>-win-x64\bin       llama.dll, ggml*.dll and what they load (from the release's Windows build)
#   third_party\llama.cpp-<BUILD>-win-x64\lib       llama.lib: the release ships no import library, so one is made
#                                                   from llama.dll's export table (dumpbin, lib)
# The folder is not in git. The release and its source are the two downloads scripts\coop\stt\gguf_v54.py describes:
#   pwsh tools\setup_llama.ps1                 from scripts\coop\stt\models\llama.cpp (the Vulkan build: any vendor's GPU, and the CPU)
#   pwsh tools\setup_llama.ps1 -Release <dir> -Source <dir> -Build b11429
param(
    [string]$Build = 'b11429',
    [string]$Release = (Join-Path $PSScriptRoot "..\..\..\scripts\coop\stt\models\llama.cpp\$Build-vulkan"),
    [string]$Source = (Join-Path $PSScriptRoot "..\..\..\scripts\coop\stt\models\llama.cpp\src\llama.cpp-$Build")
)
$ErrorActionPreference = 'Stop'
$dst = Join-Path $PSScriptRoot "..\third_party\llama.cpp-$Build-win-x64"
foreach ($d in 'include', 'bin', 'lib') { New-Item -ItemType Directory -Force (Join-Path $dst $d) | Out-Null }
Copy-Item (Join-Path $Source 'include\llama.h') (Join-Path $dst 'include') -Force
Copy-Item (Join-Path $Source 'ggml\include\*.h') (Join-Path $dst 'include') -Force
Copy-Item (Join-Path $Source 'LICENSE') (Join-Path $dst 'LICENSE') -Force
# the libraries, not the tools: llama.dll, the ggml backends it loads by name, their OpenMP runtime
Get-ChildItem $Release -Filter '*.dll' | Where-Object { $_.Name -notmatch '-impl\.dll$|^mtmd|^llama-common' } | Copy-Item -Destination (Join-Path $dst 'bin') -Force
# an import library from the DLL's exports
$vs = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -property installationPath
$tools = Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') | Sort-Object Name | Select-Object -Last 1
$bin = Join-Path $tools.FullName 'bin\Hostx64\x64'
$def = Join-Path $dst 'lib\llama.def'
$names = & (Join-Path $bin 'dumpbin.exe') /nologo /exports (Join-Path $dst 'bin\llama.dll') |
    ForEach-Object { if ($_ -match '^\s+\d+\s+[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+(\S+)') { $Matches[1] } }
if (-not $names) { throw 'no exports read from llama.dll' }
Set-Content -Path $def -Value (@('LIBRARY llama', 'EXPORTS') + ($names | ForEach-Object { "    $_" })) -Encoding ascii
& (Join-Path $bin 'lib.exe') /nologo "/def:$def" /machine:x64 "/out:$(Join-Path $dst 'lib\llama.lib')" | Out-Null
"{0}: {1} exports, {2} libraries, {3:n0} MB" -f (Resolve-Path $dst), @($names).Count, (Get-ChildItem (Join-Path $dst 'bin')).Count,
    ((Get-ChildItem $dst -Recurse -File | Measure-Object Length -Sum).Sum / 1MB)
