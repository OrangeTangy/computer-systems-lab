# Required experiments and completion checklist

## Final platform decision

Prefer a native Linux machine with hardware PMU access and enough idle time for repeatable runs. A VM/WSL can be useful for coding but may not expose counters or physical topology reliably. Intel MLC supports Windows and Linux; using Windows is possible if its required access and an appropriate counter profiler are available. Read the installed MLC version's bundled documentation before selecting flags. No automatic driver installation or machine-wide tuning has been performed.

Record CPU model, logical-to-physical core mapping and core type, cache size/sharing and cache-line size, total memory and configuration, OS/kernel, tool versions, CPU frequency policy, SMT, affinity, background activity, NUMA placement, page policy, power source, and repetitions. The i5-1240P pilot needs verified core type before interpreting cache plateaus.

## Coverage matrix

| Assignment requirement | Implemented now | Remaining final work |
|---|---|---|
| Zero-queue per-level baselines | Low-concurrency dependent chain, ns/load | Verify cache topology, choose resident regions, cross-check MLC; call this low-load, not guaranteed zero-queue |
| Pattern/granularity sweep | Sequential/random latency; 64/256/1024 B strides | Controlled final run and interpretation; distinguish footprint from touched lines |
| Read/write mixes | 100% read, 100% write, 70/30, 50/50 useful-operation throughput | Corresponding loaded-latency observations and MLC cross-check; document physical mix caveats |
| Intensity sweep and knee | Hypothesis/protocol below | Concurrent bandwidth/latency collection and plots |
| Working-set/cache transitions | 4 KiB-64 MiB pilot, 256 MiB full baseline available | Verified capacity annotations and DRAM-resident confirmation |
| Cache-miss impact | Kernel and sweeps ready | Actual supported cache counters and correlation with runtime |
| TLB-miss impact | 1024 B stride provides preliminary page-locality variation | Dedicated page-locality comparison, TLB counters, verified huge pages where available |
| Pitfall demonstration | Sequential vs random dependent chain | Quantify pilot/final effect; explain prefetching and alternative causes |
| Reproducibility/AI note/report | Source, scripts, raw/processed data, initial docs | Final measurements, student review, completed analysis, GitHub publication |

## Loaded latency protocol

Use MLC's documented loaded-latency mode for the installed version. Reserve a fixed logical CPU for the latency probe, use fixed CPUs for traffic generation, and record actual CPU assignments and buffer sizes. Sweep offered load/delay with fixed pattern and mix. Collect latency and bandwidth from each same steady-state interval. Repeat at least five times in interleaved order. Repeat relevant read/write mixes; keep other knobs fixed. Save complete original output and exact commands.

Define knee operationally before inspecting results: earliest load setting reaching at least 90% of the maximum median measured bandwidth. Also show the entire curve, variability, and sensitivity to an 85%/95% threshold. This is an engineering definition, not a universal hardware constant. If the sweep does not reach saturation, report that and extend it rather than inventing a knee.

Little's Law: average outstanding bytes = bytes/s * average seconds. For request count, divide by the consistently defined request payload. Use bandwidth and mean latency for the same request population; a separate pointer-chase probe under streaming load is only a qualitative or approximate concurrency argument, not an exact measure of streamer queue occupancy.

## Counter protocol

First capture `perf list` and check supported events on the selected core type. Generic event names are not universally available and may differ across hybrid cores. Validate permissions with a small trial. Collect cycles/instructions and supported cache/TLB events in small groups to avoid heavy multiplexing; save enabled/running percentages. Never treat unsupported events as zero.

`perf stat` around a whole benchmark includes initialization and validation, whereas the internal timer excludes them. Use a sufficiently long timed phase and quantify this limitation, or add region-scoped counter control before making quantitative miss-rate claims. Compare fixed conditions: small vs large working set, sequential vs random, concentrated vs scattered pages. Normalize misses per operation and report runtime from the matched workload.

## Page-locality/huge-page protocol

Implement matched dependent chains over the same number of touched cache lines, packed into few pages versus distributed over many pages. Keep node count and random seed matched. Large-page comparisons must verify actual mappings (e.g. `/proc/PID/smaps`), first-touch outside timing, and keep NUMA placement fixed. If huge pages are unavailable, document that, retain the base-page locality study and counters, and state the limitation.

## Final report checklist

All tables need units and sample counts. Plot median and variability, explain the exact variability statistic. Distinguish hypotheses, observations, interpretations, and unresolved alternatives. Never assign every latency change to caches: translation, prefetching, scheduling and frequency can also contribute.
