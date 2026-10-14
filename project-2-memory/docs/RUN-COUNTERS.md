# Administrator counter collection

These steps were written for the Intel laptop (`-Profile Cache` and `-Profile TLB`). The Ryzen 5 5500 capture used `-Profile Zen3`; see [ZEN3-COUNTERS.md](ZEN3-COUNTERS.md) and the [analyzed results](../../sessions/ryzen-20261014/COUNTERS.md). Keep other benchmarks closed while collecting.

1. Open **PowerShell** using **Run as administrator**.
2. Run these commands on the current computer:

```powershell
# From the root of this checkout, with GCC on PATH:
$collector = Join-Path (Get-Location) 'project-2-memory/scripts/collect-counters.ps1'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -Profile Cache
# TLB profile below is Intel Alder Lake model 154 only:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -Profile TLB
```

The execution-policy argument applies to those PowerShell processes. The script does not change a machine-wide policy, disable security/virtualization, install a driver, or run SSD writes. It runs CPU/memory benchmarks and a scoped WPR session. If WPR is already recording for another task, the start should fail rather than cancel that session.

Each successful profile saves an ETL trace, original benchmark JSON, process IDs, commands and start/stop logs in a timestamped `project-2-memory/data/counter-captures/` folder. This directory is ignored by Git. It can contain unrelated system metadata, so raw traces are not automatically published.

After both commands finish, note the printed folder paths; the analysis step reads from them. If a command fails, keep its error output with the capture folder. Do not substitute zeros for unsupported events. A trace must be inspected and attributed to the benchmark before the report can claim measured cache/TLB counts. The whole-process scope includes initialization and must be reconciled with the internal timed loop.

The TLB profile is restricted to the verified Intel family 6, model 154 system and P-core workload on CPU 0. The XML was validated by `wpr -profiles`; actual hardware recording is a separate test. See [event semantics and limitations](../../docs/archive/SUBMISSION-GATES.md).
