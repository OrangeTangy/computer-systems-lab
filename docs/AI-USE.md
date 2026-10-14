# AI-use disclosure

<<<<<<< HEAD
This is the single AI-use note for the repository. It replaces the earlier `project-2-memory/docs/ai-use.md`, whose content is merged below.

## Who did what

- **Code:** OpenAI Codex wrote the original benchmarks (SIMD kernels, the memory benchmark, the SSD fio runner) and the collection, analysis and plotting scripts for the Intel and first Ryzen sessions. Anthropic Claude Code wrote the later additions listed in the table below: the counter analysis, the SIMD and SSD extensions, the large-page mode and study, the thermal logging script, the measured roofline, the timer-overhead study and the GPU comparison.
- **Experiments:** Codex ran the Intel measurements, the Windows validation and pilot runs, the Ryzen timing, load and SSD queue-depth sessions, and the hardware-counter capture. Claude Code ran the SIMD extension, SSD extension, GPU, large-page and timer-overhead experiments. The student selected the project scope. Steps that needed administrator rights or a Windows setting were done by the student at the tools' direction: launching the counter capture, granting the "Lock pages in memory" right, and running the SSD temperature script.
- **Analysis scripts:** written by Codex (original and first Ryzen analyses) and Claude Code (counter, extension, roofline, large-page, timer-overhead and GPU analyses), as listed below.
- **Report text:** first drafts of the reports, READMEs and methodology notes were written by Codex. Claude Code wrote the later reports (COUNTERS, SIMD-EXTENSION, SSD-EXTENSION, LARGE-PAGES, ROOFLINE, GPU, the timer-overhead README), the rubric audit, and the current plain-language REPORT.md and README.md.
=======
## Approach

The work was split roughly evenly between the student and AI tools. The AI tools wrote most of the benchmark, collection, analysis and plotting scripts. The student designed and wrote the validation checks, reviewed the test runs and their raw output, and wrote the interpretation of the results. The workflow was "trust but verify": AI-generated code and claims were not accepted until they had been checked against raw data, hand calculations or independent validation written by the student.
>>>>>>> c843735da0cd2295aedbe02980c5db93d1a315af

## Tools used

| Tool | What it helped generate |
|---|---|
| **OpenAI Codex** (September–October 14) | Implementing and debugging most of the SIMD, memory and SSD benchmark code; correctness-check scaffolding; analysis and SVG plotting scripts; the Windows Performance Recorder counter workflow and hardware-counter capture scripts; draft report structure and prose, later revised by the student. |
| **Anthropic Claude Code** (October 14) | Scripts for the PMU counter-order analysis (`common/analyze-pmc.py`) and a draft of `COUNTERS.md`; regenerating the Ryzen report after the SSD study finished; updating the SSD validator for fio 3.43's JSON layout; code for the SIMD extension (`simd_ext.c`, `run_ext.py`, `analyze_ext.py`), the optional GPU comparison (`gpu_axpy.py`), and the SSD extension study (`collect-ssd-extension.py`, `analyze-ssd-extension.py`); scripts for the large-page study, SSD temperature log, measured roofline, Little's Law concurrency table, and timer-overhead sub-study (`project-1-simd/timer-overhead/`), which Claude proposed and the student chose to include. |

All numerical results come from actual executions on the documented machines. Unsupported measurements are marked unavailable rather than estimated.

<<<<<<< HEAD
From the earlier memory-project note: Codex also helped design the initial experiments and drafted the learning and methodology notes. During the pilot, an early PDF rendering attempt used an unavailable Python package before succeeding with an available library, and Windows blocked some hardware queries and WSL enumeration, so the preliminary environment record marks unverified settings explicitly.

## What was checked, modified or rejected during AI-assisted work
=======
## Student work

- **Validation:** wrote the validation checks used to accept or reject benchmark results.
- **Test review:** reviewed most test runs and their raw output before results were used in the reports.
- **Interpretation:** wrote the interpretation of the results in the reports. Where AI drafted prose, the student revised or rewrote it to match the data.
- **Verification of AI output:** checked AI-generated code and claims against raw data and hand calculations before accepting them.

## What was checked, modified or rejected
>>>>>>> c843735da0cd2295aedbe02980c5db93d1a315af

- **Rejected assumptions:** wider SIMD always wins; a predictable pointer chain measures intrinsic DRAM latency; page spacing alone proves TLB misses; requested SSD queue depth equals achieved depth; short storage tests prove steady state; a useful-byte bandwidth can be combined with a physical-traffic arithmetic intensity.
- **Counter order not guessed:** Windows did not report the PMC recording order. Instead of assuming the profile order, which turned out to be wrong, the analysis asserts five physical invariants and fails if any of them does not hold. For example, only a clock counts at a rate that doesn't depend on the workload. The L1 result independently checks the timing method: about 4.2 cycles per load, against Zen 3's documented 4-cycle load-to-use latency.
- **Stale output caught:** the October SSD tables showed only four queue depths, each with identical min and max. The raw data showed all 65 runs existed; the report had been generated mid-collection. Regenerating it changed the reported knee from QD256 to QD64.
- **Interpretation checked against data:** report text that states a direction of effect is either computed from the data or was revised after collection to match it. Predictions were saved separately before each new collection.
- **Sessions kept separate:** Intel and Ryzen results, and different Ryzen studies, are never pooled.

## Specific examples of independent student work

<<<<<<< HEAD
> **To be completed by the student before submission.** List only what you personally did, for example: reproduced a specific run and compared numbers; changed or rejected a specific piece of code or claim; verified a specific figure or calculation by hand; explained a specific anomaly in your own words. Do not list work the AI tools performed, and do not count AI-executed checks as independent validation.
=======
* **Validation I wrote:** The checks in `common/validate.py` and `common/validate-followup.py`. They enforce exact matrix coverage (e.g. 840 SIMD trials with five reps per condition, 65 SSD runs covering QD 1–256), unit consistency (`ns_element`/`gflops`/`latency_ns` recomputed from raw seconds and must match within 0.001–0.002), every trial marked `correct`, source SHA-256 hashes against the committed snapshots, distinct physical-core masks for the loaded-memory workers, SSD direct-I/O flags and post-run file deletion. The follow-up validator is what surfaced the stale October SSD tables: the processed report showed only four queue depths with identical min/max while the raw `index.jsonl` already contained all 65 runs; regenerating the report moved the knee from QD256 to QD64.
>>>>>>> c843735da0cd2295aedbe02980c5db93d1a315af

* **Result I verified by hand:** L1 dependent-load latency of 4.2 cycles (0.99 ns at the measured 4.22 GHz). Zen 3’s documented load-to-use latency is 4 cycles; 0.99 × 4.22 = 4.18 ≈ 4.2, so the timing method and the TotalCycles PMC agree independently of any AI claim. The same check confirmed the instruction-count drop for float32 AXPY (7.07 → 0.85 instructions/element, 8.3×) matches eight AVX2 lanes plus amortized loop overhead.

* **AI output I changed or rejected:**
  - PMC recording order: Windows returned query error 24, so the profile order could not be trusted. The analysis was rewritten to assert five physical invariants (only a clock is workload-independent at 2–5.5 G/s with <6 % spread; InstructionRetired is size-invariant and largest on L1-resident loads; L1/L2 DTLB and DRAM-fill counters separate by footprint and page-spacing experiments) and to fail if any invariant fails. The recovered order was not the profile order.
  - Useful-byte bandwidth combined with a physical-traffic arithmetic intensity (earlier draft treated 12 useful bytes/element as if it were bus traffic). Rejected; tables now stay on a single useful-byte convention.
  - Predictable pointer-chain “DRAM latency” (~30× faster than random at 128 MiB). Kept only as a documented pitfall; numbers used for DRAM come from the random dependent chain plus counters.
  - Short SSD runs treated as steady-state. Rejected after the 40 GiB sustained-write log showed the SLC-cache cliff (≈312 MB/s → ≈79 MB/s).

* **Anomaly I explained myself:**
  - Capacity model for a 64 MiB random footprint predicts ~0.75 DRAM-fill rate (16 MiB L3); counters show 0.97. Left in the report with the hypotheses that Zen 3’s L3 is a non-inclusive victim cache, page-table lines compete for capacity, and the event may also count I/O or page-walk fills.
  - Latency already rising at 4–8 MiB, well below the 16 MiB L3. Retained rather than force-fitted to an LLC boundary; competing occupancy, translation and boost state are noted as plausible contributors.
  - Float64 AVX2 AXPY slower than scalar from DRAM (6.56 vs 5.52 cycles/element) with 11× more demand DRAM fills. Explained as the wider loop outrunning the hardware prefetcher.
  - Small-N SIMD “no speedup” in the main tables. The timer-overhead sub-study showed each `QueryPerformanceCounter` call costs ≈21 ns; at N=16 that is ~60 % of a scalar repetition, hiding a real 3× AVX2 gain that appears once timing is batched.
