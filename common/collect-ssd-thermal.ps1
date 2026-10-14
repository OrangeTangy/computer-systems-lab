# Log SSD temperature every ~2 s across idle, a sustained sequential write, and recovery.
# Run in an ADMINISTRATOR PowerShell from the repository root (reliability counters need elevation):
#   ./common/collect-ssd-thermal.ps1 -Session ryzen-20261014 -Fio C:/path/to/fio.exe
# Writes one new disposable file inside sessions/<Session>/ssd-thermal/scratch/ and deletes exactly that file.
param(
    [Parameter(Mandatory)] [string] $Session,
    [Parameter(Mandatory)] [string] $Fio,
    [int] $SizeGiB = 30,
    [int] $IdleBeforeSeconds = 60,
    [int] $IdleAfterSeconds = 180
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$out = Join-Path $repo "sessions/$Session/ssd-thermal"
if (Test-Path $out) { throw "Refusing existing $out" }
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this in an Administrator PowerShell.' }
$scratch = Join-Path $out 'scratch'
New-Item -ItemType Directory -Force $scratch, (Join-Path $out 'raw'), (Join-Path $out 'logs') | Out-Null
$target = Join-Path $scratch 'thermal.bin'
# Full transcript, including any error, so a failed run can be diagnosed.
Start-Transcript -Path (Join-Path $out 'run-log.txt') | Out-Null
try {
$csv = Join-Path $out 'temperature.csv'
$free = (Get-PSDrive ((Get-Item $scratch).PSDrive.Name)).Free
if ($free -lt ($SizeGiB + 20) * 1GB) { throw "Need at least $($SizeGiB + 20) GiB free" }

function Read-Disk([string] $phase) {
    # Append each sample immediately so an interrupted run keeps its data.
    $r = Get-PhysicalDisk | Where-Object FriendlyName -like 'ADATA SU650*' | Get-StorageReliabilityCounter
    [pscustomobject]@{ t = [math]::Round(((Get-Date) - $script:t0).TotalSeconds, 2); temperature_c = $r.Temperature; phase = $phase } |
        Export-Csv $csv -NoTypeInformation -Append
    $script:count++
}
Set-Content (Join-Path $out 'HYPOTHESES.md') @'
# Predictions before the thermal log (written before collection)

A SATA SSD at about 300 MB/s dissipates little power, so temperature should rise only a few degrees during a 30 GiB write and stay far below typical throttling points (about 70 C). If so, the slow plateaus of the sustained-write sawtooth are SLC-cache behavior, not thermal throttling. A throughput drop that coincides with a temperature peak would contradict this.
'@
$fioConfig = Join-Path $out 'thermal-write.fio'
Set-Content $fioConfig -Encoding ascii @"
[global]
ioengine=windowsaio
direct=1
thread=1
numjobs=1
filename=thermal.bin
size=${SizeGiB}G
rw=write
bs=128k
iodepth=32
refill_buffers=1
buffer_compress_percentage=0
lat_percentiles=1
percentile_list=50:95:99:99.9
write_bw_log=thermal
write_lat_log=thermal
log_avg_msec=1000

[thermal-write]
"@
$script:count = 0
$script:t0 = Get-Date
$meta = [ordered]@{ start_local = $script:t0.ToString('o'); fio = (& $Fio --version); size_gib = $SizeGiB; idle_before_s = $IdleBeforeSeconds; idle_after_s = $IdleAfterSeconds;
    disk = (Get-PhysicalDisk | Where-Object FriendlyName -like 'ADATA SU650*' | Select-Object FriendlyName, BusType, MediaType, Size) }
Write-Host "Idle baseline $IdleBeforeSeconds s..."
while (((Get-Date) - $script:t0).TotalSeconds -lt $IdleBeforeSeconds) { Read-Disk idle-before; Start-Sleep 2 }
$meta.write_start_s = [math]::Round(((Get-Date) - $script:t0).TotalSeconds, 2)
$job = Start-Process -FilePath $Fio -ArgumentList @($fioConfig, '--output-format=json', "--output=$(Join-Path $out 'raw/thermal-write.json')") -WorkingDirectory $scratch -NoNewWindow -PassThru
# Windows PowerShell 5.1 reports an empty ExitCode unless the handle is read while the process runs.
$null = $job.Handle
Write-Host 'Sustained write running...'
while (-not $job.HasExited) { Read-Disk write; Start-Sleep 2 }
$job.WaitForExit()
if ($job.ExitCode -ne 0) { throw "fio exited with $($job.ExitCode); inspect $target before removing it" }
$meta.write_end_s = [math]::Round(((Get-Date) - $script:t0).TotalSeconds, 2)
Write-Host "Recovery $IdleAfterSeconds s..."
$end = (Get-Date).AddSeconds($IdleAfterSeconds)
while ((Get-Date) -lt $end) { Read-Disk idle-after; Start-Sleep 2 }
Get-ChildItem $scratch -Filter 'thermal_*.log' | Move-Item -Destination (Join-Path $out 'logs')
# Exact created file only.
Remove-Item -LiteralPath $target
$meta.test_file_removed = $true
$meta | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $out 'environment.json')
Write-Host "Done: $script:count temperature samples; disposable file removed."
} finally { Stop-Transcript | Out-Null }

