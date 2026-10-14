# Ryzen 5 5500 counter capture

This host is AMD family 25 (19h), model 80 (50h), with six physical Zen 3 cores and SMT enabled. The new profile is restricted to that model. XML validation is separate from successful recording; counts must be exported, attributed, and checked before use.

| Event | Encoding | Interpretation |
|---|---|---|
| LabL1DTLBMiss | Event 0x45, mask 0xFF | L1 data-TLB misses/reloads across page sizes, including hits in L2 TLB |
| LabL2DTLBMiss | Event 0x45, mask 0xF0 | Reloads that also miss L2 TLB; includes load/store activity |
| LabDemandDRAMFill | Event 0x43, mask 0x08 | Demand data-cache fills from local DRAM or I/O; not all memory-controller bytes |

Definitions: [Linux perf Zen 3 event table](https://github.com/torvalds/linux/blob/master/tools/perf/pmu-events/arch/x86/amdzen3/memory.json), [CPU-to-event-table mapping](https://github.com/torvalds/linux/blob/master/tools/perf/pmu-events/arch/x86/mapfile.csv), and [AMD uProf predefined counters](https://docs.amd.com/r/en-US/57368-uProf-user-guide/Predefined-Core-PMC-Events). Windows capture follows [Microsoft's PMU documentation](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/recording-pmu-events). The Linux mapping explicitly includes family 25 models 0x50-0x5F.

Run from the repository root in Administrator PowerShell, with GCC on PATH:

```powershell
& ./project-2-memory/scripts/collect-counters.ps1 -Profile Zen3
```

Five counters fit within the six enumerated sources, but other tools/hypervisor restrictions can still prevent registration. Strict mode must fail rather than substitute unsupported events. No persistent raw-event registration, driver installation, or security setting change is requested.

ETL is ignored by Git. Keep it local; filter to the retained PID, thread and CPU0, discard unrelated counts, inspect lost events and counter resets, and normalize using the matching benchmark's operation count. Whole-process totals include allocation, initialization, validation and teardown: label them **harness-inclusive counts per timed operation**, not exact timed-loop miss probabilities or core cycles. A long timing interval reduces but does not remove this bias. Compare equal operation counts or account for unequal timed operation counts; retain raw counts as well as normalization. Use timed-region instrumentation before claiming an exact AMAT decomposition.
