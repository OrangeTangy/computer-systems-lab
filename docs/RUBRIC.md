# Rubric audit — evidence, not a self-assigned grade

This maps the assignment's categories to evidence and explicitly identifies remaining requirements. A populated repository is not proof of full credit. Point values are copied from the assignment, not estimated scores.

## Common requirements

| Requirement | Evidence/status |
|---|---|
| AI-use note | `docs/AI-USE.md`; independent student review still needs to be documented |
| Reproducible repository | Sources, scripts, original data, processed summaries, plots and READMEs present |
| Pre-experiment hypothesis | `docs/hypotheses.md`, plus preserved original memory hypotheses |
| Correctness validation | SIMD reference checks, memory cycle/checksum checks, fio CRC32C verify pass |
| Measurement discipline | Hardware/tool/flags recorded; three repeats and min/max whiskers; frequency not fixed, no exclusive isolation |
| Negative/failure case | SIMD dot/large-array behavior; memory sequential/random and page attribution pitfalls; SSD buffered/direct comparison |
| Honest anomalies | Unexplained memory transition, non-monotonic loaded latency, and finite-run/storage-state limitations retained |

## Project 1 — 110 points

| Category | Points | Evidence and limitations |
|---|---:|---|
| Baseline, correctness, reproducibility | 15 | 450 validated trials, three builds, two data types, three kernels; out-of-place AXPY variation documented |
| Vectorization verification | 15 | Compiler reports and targeted assembly; partial vectorization of dot accurately distinguished from parallel reduction |
| Locality and memory-bound analysis | 20 | Size sweep and throughput/speedup figures; logical footprints and cache metadata; roofline uses effective bandwidth with caveats |
| Alignment, tail, stride/gather studies | 20 | Aligned/shifted start × divisible/tail sizes; stride 1/2/4/8; tables retain scalar/auto/native values |
| Roofline and quantitative insight | 20 | Arithmetic intensity, bandwidth experiment and clock-sensitive peak estimate; actual core cycles/element remain unmeasured |
| AI-use transparency and failure case | 10 | Disclosure and slower native dot/limited large-array speedup |
| Report quality | 10 | Plain-language overview, units, tables, plots and detailed limitations |

**Remaining precision gap:** TSC ticks are recorded but are not actual core cycles. A suitable native PMU run is needed for measured core cycles per element. Longer runs and improved isolation would strengthen the analysis.

The measured read-bandwidth proxy is exceeded by some main-suite kernel rates when combined with simple byte-count assumptions. The roofline report preserves this inconsistency and explains why the proxy is not a verified cross-workload upper bound. A traffic-matched bandwidth measurement/counter study would strengthen that rubric category.

## Project 2 — 185 points

| Category | Points | Evidence and limitations |
|---|---:|---|
| Zero-queue baselines | 25 | Dependent random chains and per-footprint timing; low-load rather than guaranteed zero-queue; not every cache level has an unambiguous isolated plateau |
| Pattern/granularity/RW sweeps | 35 | Sequential/random, 64/256/1024 B, four R/W mixes; loaded probe per mix; useful bytes distinguished from physical traffic |
| Throughput-latency knee | 35 | 0/1/2/4/6 worker sweep, concurrent probe; diminishing returns in some mixes, no universal saturation claim; mixed P/E worker types confound a pure concurrency comparison |
| Working-set/cache/TLB analysis | 35 | Cache topology and matched-node page-spacing sweep; **hardware cache/TLB correlations missing**, huge pages unavailable under current privilege |
| Experimental rigor | 25 | Affinity, repetitions, raw data, seeds, environment; finite probe/worker window mismatch disclosed |
| AI-use transparency and pitfall analysis | 15 | Disclosure, predictable-chain pitfall and unsupported TLB-attribution warning |
| Report quality | 15 | Detailed report, tables, plots, unresolved explanations retained |

**Not full-rubric complete:** obtain actual cache/TLB counters and matched runtime on a platform with access, strengthen isolated cache-level baselines, and extend/control load enough to establish a credible saturation knee. Huge-page testing is conditional on availability, but base-page TLB evidence still matters. Windows lists some PMC sources; recording requires privileges/access not established by enumeration. The WSL instance has no hardware CPU PMU.

## Project 3 — 185 points

| Category | Points | Evidence and limitations |
|---|---:|---|
| Safety and zero-queue baselines | 30 | File-only target, prefill, checksum verification, direct I/O, four QD1 baselines with percentiles |
| Block-size and pattern sweeps | 35 | Six sizes, random/sequential reads and writes, matched throughput/latency |
| Read/write and queue-depth analysis | 40 | Four mixes, QD1-64 plus labeled QD128/256 follow-up, same-run mean latency/IOPS, operational knee and achieved-depth data |
| Tail latency and device state | 25 | p50/p95/p99/p99.9 retained; short write series and range study; no steady-state/thermal/SLC claim |
| Reproducibility and data hygiene | 25 | Fio configs, raw JSON, index/seed, parsed summaries, scripts and repeated runs |
| AI-use transparency and pitfall analysis | 15 | AI note and buffered/direct comparison |
| Report quality | 15 | Simple explanation, technical methods, units, plots and caveats |

**Interpretation limits:** short trials and a limited file range cannot establish maximum sustained full-device performance. If the QD sweep never plateaus, call the knee range-limited and extend the experiment before claiming saturation. Steady-state observation is conditional in the assignment, but its absence must remain explicit.
