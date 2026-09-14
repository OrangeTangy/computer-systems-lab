# Pre-experiment hypotheses

Written before the pilot sweep. Smoke runs validated software only.

1. Random dependent-load latency should increase as the touched cache lines exceed successive cache capacities. A plateau may be blurred by associativity, shared cache use, replacement, TLB misses, and frequency changes.
2. Sequential chains should often be faster than random chains at large footprints because prefetchers can predict addresses despite the load dependency. Treating sequential-chain timing as intrinsic DRAM latency would be misleading.
3. Useful bandwidth should fall for large strides: fetching a cache line to use only 8 bytes wastes transferred data. Allocation size is not the same as touched cache-line volume. For stride >= 64 B, approximate touched cache-line volume is nodes * 64 B, assuming verified 64 B lines.
4. Read/write operation mixes should change observed throughput, but ordinary cached stores introduce write allocation and deferred writeback. An application-level 70/30 mix is not necessarily a DRAM-bus 70/30 mix.
5. Increasing independent memory requests should initially raise bandwidth. Near saturation, additional load should increase latency more than throughput. Loaded latency must be collected concurrently with bandwidth, not combined from unrelated runs.
6. Spreading accesses over more pages should increase translation pressure. Huge pages may reduce it where supported, but a page-size change must be verified and does not guarantee a speedup.

Record deviations and plausible alternatives; do not revise these predictions to match the measurements.
