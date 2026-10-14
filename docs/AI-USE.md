# AI-use disclosure

## Tools used

| Tool | What it helped generate |
|---|---|
| **OpenAI Codex** (September–October 14) | Interpreting the assignment; implementing and debugging the SIMD, memory and SSD benchmarks; running the Intel and Ryzen measurement sessions; correctness checks; analysis and SVG plotting scripts; first drafts of the reports; the Windows Performance Recorder counter workflow and the hardware-counter capture. |
| **Anthropic Claude Code** (October 14) | Recovering the PMU counter order from physical invariants and writing the counter analysis (`common/analyze-pmc.py`, `COUNTERS.md`); regenerating the Ryzen report, which had been built while the SSD study was still running; fixing the SSD validator for fio 3.43's JSON layout; the SIMD extension (int32, stencil, gather: `simd_ext.c`, `run_ext.py`, `analyze_ext.py`); the optional GPU comparison (`gpu_axpy.py`); the SSD block-size, mix, data-pattern, buffering and sustained-write study (`collect-ssd-extension.py`, `analyze-ssd-extension.py`); and updates to the reports and rubric audit. |

All numerical results come from actual executions on the documented machines. Unsupported measurements are marked unavailable rather than estimated.

## What was checked, modified or rejected during AI-assisted work

- **Rejected assumptions:** wider SIMD always wins; a predictable pointer chain measures intrinsic DRAM latency; page spacing alone proves TLB misses; requested SSD queue depth equals achieved depth; short storage tests prove steady state; a useful-byte bandwidth can be combined with a physical-traffic arithmetic intensity.
- **Counter order not guessed:** Windows did not report the PMC recording order. Instead of assuming the profile order (which turned out to be wrong), the analysis asserts five physical invariants, for example that only a clock counts at a workload-independent rate, and fails if any of them does not hold. The L1 result (about 4.2 cycles per load against Zen 3's documented 4-cycle load-to-use latency) independently checks the timing method.
- **Stale output caught:** the October SSD tables showed only four queue depths, each with identical min and max. Inspection of the raw data showed all 65 runs existed; the report had been generated mid-collection. Regenerating it changed the reported knee from QD256 to QD64.
- **Pre-written interpretation checked against data:** report text that states a direction of effect is either computed from the data or was revised after collection to match it; predictions were saved separately before each new collection.
- **Sessions kept separate:** Intel and Ryzen results, and different Ryzen studies, are never pooled.

## Independent student work

> **To be completed by the student before submission.** List only what you personally did, for example: reproduced a specific run and compared numbers; changed or rejected a specific piece of code or claim; verified a specific figure or calculation by hand; explained a specific anomaly in your own words. Do not list work the AI tools performed.

-
-
-
