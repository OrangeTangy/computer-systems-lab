# Report working outline — incomplete

1. Research question and pre-experiment hypotheses (`hypotheses.md`).
2. Machine/tool configuration and measurement controls, including unknowns.
3. Correctness checks, dependent latency vs independent throughput, warm-up and repetitions.
4. Per-level latency table after topology verification; cache-transition plot.
5. Pattern/stride and read/write mix results with precise byte definitions.
6. Concurrent loaded-latency/bandwidth curve, knee criterion and Little's Law limitations.
7. Cache and TLB counter correlations; page-locality and huge-page results/availability.
8. Misleading benchmark demonstration, anomalies, and alternative explanations.
9. Architectural implications for memory systems and accelerator data movement. CPU results are not measurements of Tenstorrent hardware or DRAM-chip-internal timing.
10. Reproduction instructions and honest AI disclosure.

Do not submit this outline as a finished report. Missing experiments are tracked in `experiment-plan.md`.
