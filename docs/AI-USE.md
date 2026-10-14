# AI-use disclosure

This is the single AI-use note for the repository. It replaces the earlier `project-2-memory/docs/ai-use.md`, whose content is merged below.

## Who did what

- **Code:** OpenAI Codex wrote the original benchmarks (SIMD kernels, the memory benchmark, the SSD fio runner) and the collection, analysis and plotting scripts for the Intel and first Ryzen sessions. Anthropic Claude Code wrote the later additions listed in the table below: the counter analysis, the SIMD and SSD extensions, the large-page mode and study, the thermal logging script, the measured roofline, the timer-overhead study and the GPU comparison.
- **Experiments:** Codex ran the Intel measurements, the Windows validation and pilot runs, the Ryzen timing, load and SSD queue-depth sessions, and the hardware-counter capture. Claude Code ran the SIMD extension, SSD extension, GPU, large-page and timer-overhead experiments. The student selected the project scope. Steps that needed administrator rights or a Windows setting were done by the student at the tools' direction: launching the counter capture, granting the "Lock pages in memory" right, and running the SSD temperature script.
- **Analysis scripts:** written by Codex (original and first Ryzen analyses) and Claude Code (counter, extension, roofline, large-page, timer-overhead and GPU analyses), as listed below.
- **Report text:** first drafts of the reports, READMEs and methodology notes were written by Codex. Claude Code wrote the later reports (COUNTERS, SIMD-EXTENSION, SSD-EXTENSION, LARGE-PAGES, ROOFLINE, GPU, the timer-overhead README), the rubric audit, and the current plain-language REPORT.md and README.md.

## Tools used

| Tool | What it helped generate |
|---|---|
| **OpenAI Codex** (September–October 14) | Interpreting the assignment; implementing and debugging the SIMD, memory and SSD benchmarks; running the Intel and Ryzen measurement sessions; correctness checks; analysis and SVG plotting scripts; first drafts of the reports; the Windows Performance Recorder counter workflow and the hardware-counter capture. |
| **Anthropic Claude Code** (October 14) | Recovering the PMU counter order from physical invariants and writing the counter analysis (`common/analyze-pmc.py`, `COUNTERS.md`); regenerating the Ryzen report, which had been built while the SSD study was still running; fixing the SSD validator for fio 3.43's JSON layout; the SIMD extension (int32, stencil, gather: `simd_ext.c`, `run_ext.py`, `analyze_ext.py`); the optional GPU comparison (`gpu_axpy.py`); the SSD block-size, mix, data-pattern, buffering and sustained-write study (`collect-ssd-extension.py`, `analyze-ssd-extension.py`); and updates to the reports and rubric audit. Later the same day, the large-page study, the SSD temperature log, the measured roofline, the Little's Law concurrency table, and the timer-overhead sub-study (`project-1-simd/timer-overhead/`), which Claude proposed and then carried out at the student's request. |

All numerical results come from actual executions on the documented machines. Unsupported measurements are marked unavailable rather than estimated.

From the earlier memory-project note: Codex also helped design the initial experiments and drafted the learning and methodology notes. During the pilot, an early PDF rendering attempt used an unavailable Python package before succeeding with an available library, and Windows blocked some hardware queries and WSL enumeration, so the preliminary environment record marks unverified settings explicitly.

## What was checked, modified or rejected during AI-assisted work

- **Rejected assumptions:** wider SIMD always wins; a predictable pointer chain measures intrinsic DRAM latency; page spacing alone proves TLB misses; requested SSD queue depth equals achieved depth; short storage tests prove steady state; a useful-byte bandwidth can be combined with a physical-traffic arithmetic intensity.
- **Counter order not guessed:** Windows did not report the PMC recording order. Instead of assuming the profile order (which turned out to be wrong), the analysis asserts five physical invariants, for example that only a clock counts at a workload-independent rate, and fails if any of them does not hold. The L1 result (about 4.2 cycles per load against Zen 3's documented 4-cycle load-to-use latency) independently checks the timing method.
- **Stale output caught:** the October SSD tables showed only four queue depths, each with identical min and max. Inspection of the raw data showed all 65 runs existed; the report had been generated mid-collection. Regenerating it changed the reported knee from QD256 to QD64.
- **Pre-written interpretation checked against data:** report text that states a direction of effect is either computed from the data or was revised after collection to match it; predictions were saved separately before each new collection.
- **Sessions kept separate:** Intel and Ryzen results, and different Ryzen studies, are never pooled.

## Independent student work

> **To be completed by the student before submission.** List only what you personally did, for example: reproduced a specific run and compared numbers; changed or rejected a specific piece of code or claim; verified a specific figure or calculation by hand; explained a specific anomaly in your own words. Do not list work the AI tools performed, and do not count AI-executed checks as independent validation.

-
-
-
