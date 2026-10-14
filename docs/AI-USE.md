# AI-use disclosure

## Approach

The work was split roughly evenly between the student and AI tools. The AI tools wrote most of the benchmark, collection, analysis and plotting scripts. The student designed and wrote the validation checks, reviewed the test runs and their raw output, and wrote the interpretation of the results. The workflow was "trust but verify": AI-generated code and claims were not accepted until they had been checked against raw data, hand calculations or independent validation written by the student.

## Tools used

| Tool | What it helped generate |
|---|---|
| **OpenAI Codex** (September–October 14) | Implementing and debugging most of the SIMD, memory and SSD benchmark code; correctness-check scaffolding; analysis and SVG plotting scripts; the Windows Performance Recorder counter workflow and hardware-counter capture scripts; draft report structure and prose, later revised by the student. |
| **Anthropic Claude Code** (October 14) | Scripts for the PMU counter-order analysis (`common/analyze-pmc.py`) and a draft of `COUNTERS.md`; regenerating the Ryzen report after the SSD study finished; updating the SSD validator for fio 3.43's JSON layout; code for the SIMD extension (`simd_ext.c`, `run_ext.py`, `analyze_ext.py`), the optional GPU comparison (`gpu_axpy.py`), and the SSD extension study (`collect-ssd-extension.py`, `analyze-ssd-extension.py`); scripts for the large-page study, SSD temperature log, measured roofline, Little's Law concurrency table, and timer-overhead sub-study (`project-1-simd/timer-overhead/`), which Claude proposed and the student chose to include. |

All numerical results come from actual executions on the documented machines. Unsupported measurements are marked unavailable rather than estimated.

## Student work

- **Validation:** wrote the validation checks used to accept or reject benchmark results.
- **Test review:** reviewed most test runs and their raw output before results were used in the reports.
- **Interpretation:** wrote the interpretation of the results in the reports. Where AI drafted prose, the student revised or rewrote it to match the data.
- **Verification of AI output:** checked AI-generated code and claims against raw data and hand calculations before accepting them.

## What was checked, modified or rejected

- **Rejected assumptions:** wider SIMD always wins; a predictable pointer chain measures intrinsic DRAM latency; page spacing alone proves TLB misses; requested SSD queue depth equals achieved depth; short storage tests prove steady state; a useful-byte bandwidth can be combined with a physical-traffic arithmetic intensity.
- **Counter order not guessed:** Windows did not report the PMC recording order. Instead of assuming the profile order, which turned out to be wrong, the analysis asserts five physical invariants and fails if any of them does not hold. For example, only a clock counts at a rate that doesn't depend on the workload. The L1 result independently checks the timing method: about 4.2 cycles per load, against Zen 3's documented 4-cycle load-to-use latency.
- **Stale output caught:** the October SSD tables showed only four queue depths, each with identical min and max. The raw data showed all 65 runs existed; the report had been generated mid-collection. Regenerating it changed the reported knee from QD256 to QD64.
- **Interpretation checked against data:** report text that states a direction of effect is either computed from the data or was revised after collection to match it. Predictions were saved separately before each new collection.
- **Sessions kept separate:** Intel and Ryzen results, and different Ryzen studies, are never pooled.

## Specific examples of independent student work

> Replace these with concrete instances.

- Validation I wrote: <which check, and what it caught or confirmed>
- Result I verified by hand: <figure or calculation, and how>
- AI output I changed or rejected: <code or claim, and why>
- Anomaly I explained myself: <what it was, and my explanation>
