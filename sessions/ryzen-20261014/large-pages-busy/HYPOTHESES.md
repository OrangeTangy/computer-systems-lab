# Predictions before the large-page study (written before collection)

- 2 MiB pages cover 512 times more memory per TLB entry. The 2,048-entry L2 DTLB then reaches 4 GiB, so every footprint here should be translated without page walks.
- **Scattered chain:** with 4 KiB pages it took about 98 cycles/load against 43 for the same 16,384 nodes packed, and the counters showed 0.66 L2-DTLB misses per load. If page walks caused the gap, large pages should bring the scattered chain close to the packed one. Any remaining gap would come from 4 KiB set aliasing (every node maps to the same L1/L2 set index), which large pages do not change.
- **Footprint sweep:** small for 4 MiB (no L2-DTLB misses even with 4 KiB pages), larger for 64-256 MiB, where base pages walk on most loads. DRAM access itself remains, so large pages should reduce, not remove, the DRAM-region latency.
