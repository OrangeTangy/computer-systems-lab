$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this script in Administrator PowerShell.' }
$compilerBin = Join-Path (Split-Path $repo -Parent) 'tools\w64devkit\bin'
if (Test-Path (Join-Path $compilerBin 'gcc.exe')) { $env:PATH = $compilerBin + ';' + $env:PATH }
Write-Host 'Waiting for the timing suites to finish so the captures do not overlap.'
$deadline = (Get-Date).AddMinutes(40)
while (-not (Test-Path (Join-Path $repo 'sessions\ryzen-20261014\timing-complete.flag'))) {
    if ((Get-Date) -gt $deadline) { throw 'timing-complete.flag is absent. Create it in the session folder once the timing suites have finished.' }
    Start-Sleep -Seconds 5
}
& (Join-Path $repo 'project-2-memory\scripts\collect-counters.ps1') -Profile Zen3
