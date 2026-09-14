# Pilot observations

Source run: `pilot-20260910T010006.816256Z`. 510 successful trials; 170 conditions.

These are preliminary measurements, not final per-cache latency claims. Error whiskers are min-max, not confidence intervals.

| Footprint | Random 64 B dependent-load median (ns) | Sequential 64 B median (ns) |
|---|---:|---:|
| 4 KiB | 1.38 | 1.42 |
| 16 KiB | 1.42 | 1.39 |
| 64 KiB | 4.44 | 1.42 |
| 256 KiB | 4.25 | 1.39 |
| 1,024 KiB | 7.87 | 1.57 |
| 4,096 KiB | 135.51 | 2.47 |
| 16,384 KiB | 153.13 | 6.51 |
| 65,536 KiB | 159.67 | 6.72 |

Interpretation: a regular dependent chain can still benefit from hardware prefetching. The random chain reduces predictability. Large random footprints may include TLB/page-walk costs as well as DRAM latency.

Do not infer peak DRAM bandwidth from this scalar single-thread kernel. Mix percentages describe operations (last partial group can differ slightly), not physical bus read/write ratios. Strided tests touch only one 8-byte value per selected location; allocation size alone is not cache occupancy.

Still required: verified core/cache topology and final environment, sustained/loaded latency and concurrency experiments, hardware cache/TLB counters, page-locality experiments, and the completed report.