# Quantitative roofline interpretation

Five independent native executions read a 256 MiB array with four AVX2 accumulators on logical CPU 0. Every scan is consumed and an initial exact sum is validated. The footprint exceeds the reported 12 MiB LLC. Median useful read bandwidth: **17.13 GB/s** (trial range 16.49–17.41 GB/s). This is effective sustained single-thread read bandwidth, not a memory-controller counter or socket maximum.

| Float32 kernel | Useful intensity (FLOP/byte) | B × intensity (GFLOP/s) |
|---|---:|---:|
| AXPY | 2/12 | 2.86 |
| Multiply | 1/12 | 1.43 |
| Dot | 2/8 | 4.28 |

For out-of-place AXPY/multiply with ordinary cached stores, write allocation may add one extra output-sized transfer: 16 bytes rather than 12 bytes per float element. That lowers the illustrative bounds to **2.14 GFLOP/s** for AXPY and **1.07 GFLOP/s** for multiply. A read-only bandwidth ceiling is only a proxy for these mixed read/write kernels; read/write resource asymmetry and CPU instruction costs can make the real bound lower.

## Compute ceiling and clock sensitivity

For a P-core model with two 256-bit FMA issue slots, FP32 peak is 2 instructions/cycle × 8 lanes × 2 FLOPs/FMA = **32 FLOPs/cycle**. At illustrative 1, 2, 3 and 4 GHz this is 32, 64, 96 and 128 GFLOP/s. These are estimates, not measured clocks. Our main suite disables FMA contraction, so this FMA-capable hardware ceiling is deliberately optimistic and not an expected achieved rate. Separate multiply/add can impose a tighter instruction-throughput ceiling (approximately 16 FP32 FLOPs/cycle under a two-vector-op/cycle model).

The [Intel optimization manual](https://cdrdv2-public.intel.com/814198/248966-Optimization-Reference-Manual-V1-049.pdf) describes Golden Cove execution resources; use the AVX2 client case, not a server AVX-512 peak. Native CPUID reports a P-core and AVX2 is exercised by the executable.

## Interpretation

Measured native float32 large-N AXPY is about 3.03 GFLOP/s and multiply about 1.60 GFLOP/s. Both are far below even conservative clock-sensitive compute ceilings. Their low arithmetic intensity, falling scalar-to-vector speedup, large footprint, and measured bandwidth envelope support a data-movement-limited interpretation. Exact DRAM traffic and actual core cycles remain unmeasured. The ordered dot reduction can remain dependency-limited even when its arithmetic intensity is somewhat higher.

**Model mismatch to retain:** compare those observations directly with the table. An observation above `B * intensity` means this separately measured read bandwidth is not a valid universal roof for that workload/session. Read/write asymmetry, cached or deferred stores, differing footprints and frequency/device state can change effective bandwidth. The store-traffic estimate is especially uncertain without counters. Therefore the figure is a sensitivity model using a measured bandwidth proxy, not a verified hard upper envelope. The data-movement explanation is supported by several trends but not proved by this proxy alone.

TSC ticks per element in the original data are **reference-clock ticks**, not core cycles; changing core frequency makes them different. Do not divide by a nominal GHz value and claim measured core cycles.
