param([ValidateSet('Cache','TLB','Zen3')][string]$Profile = 'Cache', [ValidateSet('LLCMisses','DcacheMisses','CacheMisses')][string]$CacheEvent = 'LLCMisses')
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
$simdBuilds = @()
$queryExe = Join-Path $buildDir 'query-pmc-order.exe'
& $compiler.Source '-O2' (Join-Path $repoRoot 'common\query-pmc-order.c') '-ladvapi32' '-o' $queryExe
if ($LASTEXITCODE -ne 0) { throw 'Counter-order query build failed.' }
foreach ($dtype in @('float','double')) {
    foreach ($variant in @('scalar','auto','native')) {
        $simd = Join-Path $buildDir "simd-$dtype-$variant.exe"
        $flags = @('-O3','-ffp-contract=off',"-DTYPE=$dtype")
        if ($variant -eq 'scalar') { $flags += '-fno-tree-vectorize' }
        if ($variant -eq 'native') { $flags += '-march=native' }
        & $compiler.Source @flags (Join-Path $repoRoot 'project-1-simd\src\simd.c') '-o' $simd
        if ($LASTEXITCODE -ne 0) { throw 'SIMD counter build failed.' }
        $simdBuilds += @{Exe=$simd;Type=$dtype;Variant=$variant;Flags=$flags}
    }
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outputDir = Join-Path $projectRoot "data\counter-captures\$stamp-$Profile"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
@{cpu=(Get-ItemPropertyValue 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0' 'Identifier');compiler=(& $compiler.Source --version);simdBuilds=$simdBuilds} | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $outputDir 'environment.json')
Copy-Item (Join-Path $projectRoot 'src\membench.c') (Join-Path $outputDir 'membench.c')
Copy-Item (Join-Path $repoRoot 'project-1-simd\src\simd.c') (Join-Path $outputDir 'simd.c')
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
if ($Profile -eq 'Zen3') {
    $cpu = Get-ItemPropertyValue 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0' 'Identifier'
    if ($cpu -notmatch 'Family 25 Model 80 ') { throw 'Zen3 profile requires the verified Ryzen family 25 model 80.' }
    $profileFile = Join-Path $projectRoot 'docs\counters-zen3.wprp'
    $profileName = 'LabCountersZen3'
}
if ($Profile -eq 'Cache') {
    $generatedProfile = Join-Path $outputDir 'profile.wprp'
    (Get-Content -LiteralPath $profileFile -Raw).Replace('LLCMisses', $CacheEvent) | Set-Content -LiteralPath $generatedProfile -Encoding utf8
    $profileFile = $generatedProfile
}
$trace = Join-Path $outputDir 'counters.etl'
$started = $false
try {
    & wpr -start "$profileFile!$profileName" -filemode 2>&1 | Tee-Object -FilePath (Join-Path $outputDir 'start.txt')
    if ($LASTEXITCODE -ne 0) { throw "WPR could not start. Read $outputDir\start.txt. No counter values will be invented." }
    $started = $true
    & $queryExe 2>&1 | Set-Content (Join-Path $outputDir 'counter-order.txt')
    & wpr -pmcsources | Set-Content (Join-Path $outputDir 'active-sources.txt')
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
    foreach ($build in $simdBuilds) {
        foreach ($n in @(1024,16777216)) {
            for ($rep = 0; $rep -lt 3; $rep++) {
                $tag = "simd-$($build.Type)-$($build.Variant)-$n-$rep"
                $arguments = @([string]$n,'1','0','0','3')
                $stdout = Join-Path $outputDir "$tag.json"
                $stderr = Join-Path $outputDir "$tag.stderr.txt"
                $begin = [DateTime]::UtcNow.ToString('o')
                $process = Start-Process -FilePath $build.Exe -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput $stdout -RedirectStandardError $stderr
                if ($process.ExitCode -ne 0) { throw "SIMD benchmark $tag failed." }
                $row = Get-Content -LiteralPath $stdout -Raw | ConvertFrom-Json
                if (-not $row.correct) { throw "SIMD correctness failed in $tag" }
                @{tag=$tag;pid=$process.Id;cpu=0;begin_utc=$begin;end_utc=[DateTime]::UtcNow.ToString('o');arguments=$arguments;profile=$Profile} | ConvertTo-Json -Compress | Add-Content (Join-Path $outputDir 'index.jsonl')
                Write-Host "Captured $tag"
            }
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
