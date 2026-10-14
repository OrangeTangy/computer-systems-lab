# AI-use disclosure

## Approach

Work was split roughly evenly. AI wrote most of the benchmark, collection, analysis and plotting scripts, plus most of the report and doc prose (including this file, README.md, REPORT.md and the session reports). I designed and wrote the validation checks, reviewed the test runs and raw output, and wrote or heavily revised the interpretation of the results. Nothing from the AI was accepted until it had been checked against raw data, hand calculations or the independent validation I wrote.

## Tools used

| Tool | What it helped generate |
|---|---|
| **OpenAI Codex** (September–October 14) | Most of the SIMD, memory and SSD benchmark code; correctness-check scaffolding; analysis and SVG plotting scripts; the Windows Performance Recorder counter workflow and hardware-counter capture scripts; draft report structure and prose (later revised). |
| **Anthropic Claude Code** (October 14) | PMU counter-order analysis (`common/analyze-pmc.py`) and a draft of `COUNTERS.md`; regenerating the Ryzen report after the SSD study finished; updating the SSD validator for fio 3.43's JSON layout; SIMD extension (`simd_ext.c`, `run_ext.py`, `analyze_ext.py`), optional GPU comparison (`gpu_axpy.py`), SSD extension study (`collect-ssd-extension.py`, `analyze-ssd-extension.py`); large-page study, SSD temperature log, measured roofline, Little's Law concurrency table, and timer-overhead sub-study (`project-1-simd/timer-overhead/`). Claude proposed the last few; I chose which ones to keep. |
| **xAI Grok** (October 14) | README.md, REPORT.md, this AI-USE note, OCTOBER-AUDIT.md and most of the other docs / session report prose. I revised the interpretation sections and filled the concrete student-work examples. |

All numbers come from actual runs on the documented machines. Unsupported measurements are marked unavailable, not estimated.

## Student work

- Wrote the validation checks that accept or reject benchmark results.
- Reviewed most test runs and their raw output before anything went into the reports.
- Wrote or heavily revised the interpretation in the reports. Where AI drafted prose, I changed it to match the data.
- Checked AI-generated code and claims against raw data and hand calculations before accepting them.

## What was checked, modified or rejected

- Rejected assumptions: wider SIMD always wins; a predictable pointer chain measures intrinsic DRAM latency; page spacing alone proves TLB misses; requested SSD queue depth equals achieved depth; short storage tests prove steady state; a useful-byte bandwidth can be combined with a physical-traffic arithmetic intensity.
- Counter order was not guessed. Windows did not report the PMC recording order. Instead of assuming the profile order (which turned out wrong), the analysis asserts five physical invariants and fails if any of them does not hold. Only a clock counts at a rate that does not depend on the workload. The L1 result also checks the timing method: about 4.2 cycles per load, against Zen 3's documented 4-cycle load-to-use latency.
- Stale output caught: the October SSD tables showed only four queue depths, each with identical min and max. The raw data had all 65 runs; the report had been generated mid-collection. Regenerating it changed the reported knee from QD256 to QD64.
- Interpretation was checked against the data. Any claim about direction of effect is either computed from the data or was revised after collection to match it. Predictions were saved separately before each new collection.
- Sessions were kept separate. Intel and Ryzen results, and different Ryzen studies, are never pooled.

## Specific examples of independent student work

- **Validation I wrote:** The checks in `common/validate.py` and `common/validate-followup.py`. They enforce exact matrix coverage (840 SIMD trials with five reps per condition, 65 SSD runs covering QD 1–256), unit consistency (`ns_element` / `gflops` / `latency_ns` recomputed from raw seconds), every trial marked correct, source SHA-256 hashes against the committed snapshots, distinct physical-core masks for the loaded-memory workers, SSD direct-I/O flags and post-run file deletion. The follow-up validator is what caught the stale SSD tables: the processed report only had four queue depths while `index.jsonl` already had all 65 runs. Regenerating moved the knee from QD256 to QD64.

- **Result I verified by hand:** L1 dependent-load latency of 4.2 cycles (0.99 ns at the measured 4.22 GHz). Zen 3's documented load-to-use is 4 cycles; 0.99 × 4.22 ≈ 4.2, so the timer and the TotalCycles PMC agree. Same check confirmed the float32 AXPY instruction drop (7.07 → 0.85 instructions/element).

- **AI output I changed or rejected:**
  - PMC recording order. Windows returned query error 24, so the profile order could not be trusted. Rewrote the analysis to assert five physical invariants and fail if any does not hold. Recovered order was not the profile order.
  - Combining useful-byte bandwidth with a physical-traffic arithmetic intensity. Rejected; tables now stay on one useful-byte convention.
  - Predictable pointer-chain “DRAM latency” (~30× faster than random at 128 MiB). Kept only as a documented pitfall. DRAM numbers come from the random dependent chain plus counters.
  - Short SSD runs treated as steady-state. Rejected after the 40 GiB sustained-write log showed the SLC-cache cliff (≈312 MB/s → ≈79 MB/s).

- **Anomaly I explained myself:**
  - Capacity model for a 64 MiB random footprint predicts ~0.75 DRAM-fill rate; counters show 0.97. Left in with the note that Zen 3's L3 is a non-inclusive victim cache, page-table lines compete for capacity, and the event may also count I/O or page-walk fills.
  - Latency already rising at 4–8 MiB, well below the 16 MiB L3. Kept rather than force-fitted to an LLC boundary.
  - Float64 AVX2 AXPY slower than scalar from DRAM (6.56 vs 5.52 cycles/element) with 11× more demand DRAM fills. Wider loop outran the hardware prefetcher.
  - Small-N SIMD “no speedup” in the main tables. Timer-overhead study showed each `QueryPerformanceCounter` call costs ≈21 ns; at N=16 that is most of a scalar repetition and hides a real 3× AVX2 gain that shows up once timing is batched.
