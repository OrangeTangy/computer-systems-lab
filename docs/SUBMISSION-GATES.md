# What must be true before claiming full rubric coverage

This is a completion checklist, not a prediction of the instructor's grade. Lecture integration improves architectural interpretation; it does not replace measurements.

| Gate | Current evidence | What closes it |
|---|---|---|
| Lecture concepts connected accurately | Page-specific connections for all three supplied decks; experimental versus illustrative numbers separated | Student can explain the connections and limitations |
| Memory load placement/window controls | New five-repeat fixed-P-core delay sweep with measured lag/overhang | Review the new curve; do not call a non-plateau a saturation knee |
| Cache/TLB correlation | Administrator collector prepared; current published data has no validated PMU values | Successful capture, event attribution, matched runtime and normalized counts; unsupported events must remain missing |
| CPU cycles per element | TSC ticks available, not core cycles | Suitable core-cycle counter capture and correct timed-region or clearly labeled harness-inclusive normalization |
| Isolated cache-level latency | Topology and size sweeps; earlier LLC transition remains ambiguous | Denser measurements plus counter evidence sufficient to identify resident regimes |
| Roofline quantitative consistency | Read-bandwidth proxy and explicit mismatch documented | Workload-matched bandwidth/traffic accounting and clock-sensitive compute estimate with defensible bounds |
| SSD maximum/knee robustness | Short-run matrix and separately labeled high-QD follow-up | Repeat uncertain near-knee conditions under consistent state; distinguish maximum observed from sustained/device maximum |
| Correctness and reproducibility | Raw data, sources, scripts and automatic checks | Reproduce selected runs from a clean checkout; keep capture failures and session provenance |
| Student responsibility | AI contribution disclosed | Student performs and records independent validation and can explain submitted work |

## Counter workflow

The user indicated Administrator PowerShell is available. `project-2-memory/scripts/collect-counters.ps1` builds the benchmark, starts a strict profile, runs the matched conditions, and saves per-process IDs, commands and traces. The base cache profile and Alder Lake P-core TLB profile are separate so an unsupported custom event does not get silently substituted.

The custom TLB event is model-specific: **Alder Lake P-core DTLB_LOAD_MISSES.WALK_COMPLETED, EventSel 0x12, UMask 0x0E**. It counts completed demand-load page walks, not every L1-TLB miss; a miss satisfied by a second-level TLB need not cause this event. The authoritative definition is in [Intel's Alder Lake P-core event documentation](https://perfmon-events.intel.com/platforms/alderlake/core-events/p-core/). A different CPU/core type needs its own definitions.

WPR validated the XML profile listing in the non-elevated session. Actual registration, counting and export are not thereby validated. Filter to the benchmark process/thread and logical CPU 0; ignore unrelated system/core counts. Whole-process traces include initialization and validation, unlike internal kernel timing. Address that scope difference before computing precise miss rates or cycles per timed element. Raw ETL files remain local because they can contain unrelated system metadata.

If Windows or its hypervisor refuses a counter even with elevation, retain the error and use a supported native profiling environment. Elevation is an opportunity to collect evidence, not a guarantee that all events are available. No hypervisor/security configuration changes are part of this collector.
