# Administrator counter collection

The script is ready, but no successful elevated trace has yet been received or validated. Keep other benchmarks closed while collecting.

1. Open **PowerShell** using **Run as administrator**.
2. Run these commands on the current computer:

```powershell
$collector = 'C:\Users\raide\Documents\Codex\2026-09-09\files-mentioned-by-the-user-ecse4320\outputs\computer-systems-lab\project-2-memory\scripts\collect-counters.ps1'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -Profile Cache
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collector -Profile TLB
```

The execution-policy argument applies to those PowerShell processes. The script does not change a machine-wide policy, disable security/virtualization, install a driver, or run SSD writes. It runs CPU/memory benchmarks and a scoped WPR session. If WPR is already recording for another task, the start should fail rather than cancel that session.

Each successful profile saves an ETL trace, original benchmark JSON, process IDs, commands and start/stop logs in a timestamped `project-2-memory/data/counter-captures/` folder. This directory is ignored by Git. It can contain unrelated system metadata, so raw traces are not automatically published.

After both commands finish, tell Codex the printed folder paths or paste an error. Do not substitute zeros for unsupported events. A trace must be inspected and attributed to the benchmark before the report can claim measured cache/TLB counts. The whole-process scope includes initialization and must be reconciled with the internal timed loop.

The TLB profile is restricted to the verified Intel family 6, model 154 system and P-core workload on CPU 0. The XML was validated by `wpr -profiles`; actual hardware recording is a separate test. See [event semantics and limitations](../../docs/SUBMISSION-GATES.md).
