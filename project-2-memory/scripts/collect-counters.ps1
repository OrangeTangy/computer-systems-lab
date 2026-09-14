param([ValidateSet('Cache','TLB')][string]$Profile = 'Cache')
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Open PowerShell with Run as administrator, then rerun this script.'
}
$projectRoot = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $projectRoot -Parent
$buildDir = Join-Path $projectRoot 'build'
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
$compiler = Get-Command gcc -ErrorAction SilentlyContinue
if (-not $compiler -and (Test-Path 'C:\msys64\ucrt64\bin\gcc.exe')) {
    $compiler = Get-Command 'C:\msys64\ucrt64\bin\gcc.exe'
}
if (-not $compiler) { throw 'GCC is required. Add its bin folder to PATH.' }
$env:PATH = (Split-Path $compiler.Source -Parent) + ';' + $env:PATH
$bench = Join-Path $buildDir 'membench-counters.exe'
& $compiler.Source '-O3' '-std=c11' '-Wall' '-Wextra' (Join-Path $projectRoot 'src\membench.c') '-o' $bench
if ($LASTEXITCODE -ne 0) { throw 'Benchmark compilation failed.' }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outputDir = Join-Path $projectRoot "data\counter-captures\$stamp-$Profile"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
& wpr -pmcsources | Set-Content (Join-Path $outputDir 'sources.txt')
& wpr -status | Set-Content (Join-Path $outputDir 'initial-status.txt')
$profileFile = Join-Path $projectRoot 'docs\counters.wprp'
$profileName = 'LabCounters'
if ($Profile -eq 'TLB') {
    $cpu = Get-ItemPropertyValue 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0' 'Identifier'
    if ($cpu -notmatch 'Family 6 Model 154 ') { throw 'Custom TLB profile is restricted to verified Alder Lake model 154; do not use it on another CPU.' }
    $profileFile = Join-Path $projectRoot 'docs\counters-tlb.wprp'
    $profileName = 'LabCountersTLB'
}
$trace = Join-Path $outputDir 'counters.etl'
$started = $false
try {
    & wpr -start "$profileFile!$profileName" -filemode 2>&1 | Tee-Object -FilePath (Join-Path $outputDir 'start.txt')
    if ($LASTEXITCODE -ne 0) { throw "WPR could not start. Read $outputDir\start.txt. No counter values will be invented." }
    $started = $true
    $conditions = @(
        @{ Name='L1-candidate'; Bytes=16384; Stride=64; Pattern='random' },
        @{ Name='L2-candidate'; Bytes=262144; Stride=64; Pattern='random' },
        @{ Name='LLC-candidate'; Bytes=4194304; Stride=64; Pattern='random' },
        @{ Name='DRAM-candidate'; Bytes=67108864; Stride=64; Pattern='random' },
        @{ Name='packed-pages'; Bytes=1048576; Stride=64; Pattern='random' },
        @{ Name='scattered-pages'; Bytes=67108864; Stride=4096; Pattern='random' }
    )
    for ($rep = 0; $rep -lt 3; $rep++) {
        foreach ($case in $conditions) {
            $tag = "$($case.Name)-$rep"
            $arguments = @('latency', [string]$case.Bytes, [string]$case.Stride, $case.Pattern, '100', '3', '0', [string](4320 + $rep))
            $stdout = Join-Path $outputDir "$tag.json"
            $stderr = Join-Path $outputDir "$tag.stderr.txt"
            $begin = [DateTime]::UtcNow.ToString('o')
            $process = Start-Process -FilePath $bench -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput $stdout -RedirectStandardError $stderr
            if ($process.ExitCode -ne 0) { throw "Benchmark $tag failed; inspect $stderr" }
            $row = Get-Content -LiteralPath $stdout -Raw | ConvertFrom-Json
            if (-not $row.correct) { throw "Correctness failed in $tag" }
            @{tag=$tag;pid=$process.Id;cpu=0;begin_utc=$begin;end_utc=[DateTime]::UtcNow.ToString('o');arguments=$arguments;profile=$Profile} | ConvertTo-Json -Compress | Add-Content (Join-Path $outputDir 'index.jsonl')
            Write-Host "Captured $tag"
        }
    }
} finally {
    if ($started) {
        & wpr -stop $trace 2>&1 | Tee-Object -FilePath (Join-Path $outputDir 'stop.txt')
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Trace stop failed. Inspect WPR status; do not start another capture blindly.' }
    }
}
Write-Host "Saved $outputDir"
Write-Host 'Trace capture is not yet validated counter analysis. Return to Codex with this path.'
Write-Host 'Keep ETL local: it contains system process/module metadata. Git ignores this capture directory.'
