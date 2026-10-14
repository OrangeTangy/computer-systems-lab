# ECSE 4320/6320 class-wide projects: SIMD, memory and SSD

We ran all three projects on two machines and kept their results separate:

- An Intel i5-1240P laptop (first round, GCC 13.1, fio 3.42).
- An AMD Ryzen 5 5500 desktop with an ADATA SU650 SATA SSD and a GTX 1660 Ti (second round, October 14, GCC 16.2, fio 3.43). Most numbers below come from this machine.

Detailed results for the Ryzen machine are in `sessions/ryzen-20261014/`: the [main report](sessions/ryzen-20261014/REPORT.md), [hardware counters](sessions/ryzen-20261014/COUNTERS.md), [roofline](sessions/ryzen-20261014/ROOFLINE.md), [SIMD extension](sessions/ryzen-20261014/SIMD-EXTENSION.md), [large pages](sessions/ryzen-20261014/LARGE-PAGES.md), [SSD extension](sessions/ryzen-20261014/SSD-EXTENSION.md) and the optional [GPU comparison](sessions/ryzen-20261014/GPU.md). [OCTOBER-AUDIT.md](docs/OCTOBER-AUDIT.md) maps each rubric item to its evidence.

## How we measured

- Benchmarks run single-threaded and pinned to CPU 0. For the loaded-memory test, the extra workers run on separate physical cores.
- Every kernel's output is checked before timing: SIMD results against a double-precision reference, pointer chains for being one complete cycle, and SSD files with a CRC32C check.
- Each condition runs 3 to 5 times in shuffled order. Tables show the median with the min and max in brackets, and plots use min/max whiskers.
- We wrote our predictions in a `HYPOTHESES.md` file before each round of measurements.
- Hardware, OS, compiler flags, cache topology and power plan are saved with each session. SMT stayed on and the Balanced power plan was used, so the clock was not fixed. The cycle counter showed the cores ran at about 4.22 GHz during the tests.

## Project 1: SIMD

We tested AXPY, elementwise multiply and a dot product in float32 and float64, plus a 3-point stencil and an int32 version. Each was built three ways: scalar (`-fno-tree-vectorize`), default `-O3`, and `-O3 -march=native` (AVX2).

Vectorization is confirmed in three ways. The compiler reports show 32-byte vector loops, the disassembly shows AVX2 instructions, and the instruction counter shows float32 AXPY dropping from 7.07 to 0.85 instructions per element.

What we found:

- SIMD helps a lot in cache and little from DRAM. Float32 AXPY is 4.6x faster than scalar in L1 but only 1.1x faster once the arrays come from DRAM, where the core spends most of its time waiting for memory.
- Data type matters mostly through lane count. In cache, int32 and float32 run at the same speed (8 lanes each), and float64 is about 1.5x slower (4 lanes). From DRAM, float64 takes about 2x as long because it moves twice the bytes.
- Alignment and tails matter little. Shifting the arrays by one element or adding a leftover tail changes the time by less than 10% at 65K elements. At 16 to 19 elements the timer itself dominated; see the timer finding below.
- Stride hurts quickly. By stride 4 the vector builds lose their advantage, because each cache line delivers fewer useful elements.
- Roofline: the measured DRAM bandwidth is 15.9 GB/s and the estimated peak compute is 135 GFLOP/s (two FMA units at the measured 4.22 GHz). All our kernels sit far to the left of the ridge point (8.5 FLOP/byte), so they are memory-bound once data comes from DRAM.

Cases where SIMD did not help:

- The dot product keeps a fixed summation order, so each addition waits for the previous one. It runs at 2.55 GFLOP/s both in L1 and from DRAM, which works out to about 3.3 cycles per addition, matching the CPU's floating-point add latency.
- Float64 AXPY from DRAM was slower with AVX2 than scalar (6.56 vs 5.52 cycles per element). The counters show 11x more demand DRAM fills, which suggests the wider loop outran the hardware prefetcher.
- A gather loop (`x[idx[i]]`) gained only 1.4x even with sequential indices. Forcing real AVX2 gather instructions made it slower than plain scalar code on this CPU.

Timer finding ([details](project-1-simd/timer-overhead/README.md)): our benchmark reads the clock after every call, and each read costs about 21 ns. At very small sizes that hid most of the speedup. Timing in batches showed a 3x AVX2 speedup at N=16 instead of 1.1x, and 6.7x instead of 4.0x at N=1,024. So the small-N results in the main tables understate SIMD.

## Project 2: Cache and memory

Latency comes from a pointer chase where each load depends on the previous one, so loads cannot overlap. Using the cycle counter:

| Level | Footprint | Latency |
|---|---|---|
| L1 | 16 KiB | 4.2 cycles (0.99 ns) |
| L2 | 256 KiB | 13 cycles (3.1 ns) |
| L3 region | 4 MiB | 58 cycles (14 ns) |
| DRAM | 64 MiB | about 508 cycles (122 ns) |

The L1 number matches AMD's documented 4-cycle load latency, which also confirms our timing method.

- Cache and TLB counters: we read L1/L2 TLB misses and DRAM fills from the hardware counters, and they line up with the footprint. The 4 MiB test misses the small L1 TLB but stays in L3. The 64 MiB test misses DRAM on nearly every load and needs a page walk on about 60% of them. A simple AMAT fit gives about 53 cycles for a hit and about 470 cycles for a DRAM miss including translation.
- TLB effect: spreading the same 16,384 nodes over 16,384 pages instead of 256 raised the page walks from almost none to 0.66 per load, and the time from 43 to 98 cycles.
- Huge pages: 2 MiB pages cut DRAM-region latency by 8 to 12% at 64 to 256 MiB. They also removed about a third of the gap between spread-out and packed pages. The rest of that gap is cache-set conflicts, which bigger pages don't fix.
- Read/write mix and the knee: with 1 to 5 background workers, every read/write mix reached 90% of its maximum bandwidth at 2 workers. After that, extra workers mostly added latency (138 to 483 ns at 100% reads) instead of bandwidth. By Little's Law, each core keeps roughly 40 cache lines in flight. Past the knee the total keeps growing while bandwidth stays flat, so the extra requests just wait. Sequential vs random access and the 64/256/1024 B stride sweeps were done on the Intel laptop.

Pitfalls and anomalies:

- A predictable pointer chain looked 30x faster than a random one at 128 MiB, because the prefetcher hides DRAM. It cannot be used as a DRAM latency number.
- Running the huge-page test while other apps were busy reversed one of the results. We reran it on an idle machine and kept both runs.
- Unexplained: latency starts rising around 4 to 8 MiB, below the 16 MiB L3. The DRAM fill rate at 64 MiB is also higher than a simple capacity model predicts.

## Project 3: SSD

All tests used fio with direct I/O on new disposable files that were verified with CRC32C and deleted afterwards, never on a raw partition.

- QD1 baselines (median): 4 KiB random read 168 us (p99 259 us), 4 KiB random write 63 us, 128 KiB sequential read 310 us, 128 KiB sequential write 388 us.
- Queue depth: IOPS went from 6.9K at QD1 to 63K at QD64, our knee (the first QD within 90% of the maximum). Past QD32 throughput barely grew while latency went up about 6.5x. SATA can only hold 32 commands in the drive, so deeper queues just wait in Windows. Little's Law (IOPS x latency) matched the queue depth up to QD16. Above that it fell short, meaning fio was not actually keeping every requested I/O in flight.
- Block size: throughput rose from about 210 MB/s at 4 KiB to the SATA limit of about 450 to 540 MB/s from 16 to 32 KiB up. Random and sequential reads ended up about the same at large blocks.
- Read/write mix: a 50/50 mix was slower than either all-reads or all-writes, and read latency roughly doubled when mixed with writes.
- Tail latency and device state: a 40 GiB sustained write alternated between about 312 MB/s (writing into the SLC cache) and about 79 MB/s (writing straight to TLC while the cache emptied). So short write tests only show burst speed. Write p99 reached 30 to 100 ms when the cache was full. We also logged the drive temperature (38 to 48 °C). The drive ran at full speed while hottest, so the slowdowns come from the cache, not from overheating.
- Misleading setups: buffered I/O made the drive look 0.6x as fast on a cold file and 5x as fast on a file already in RAM. Neither number measures the SSD. Compressible data made no real difference.

## Optional: GPU

With the data already on the GPU, AXPY ran at 237 GB/s, about 14x the CPU. Counting the copies over PCIe, it was slower than the CPU (0.72x), because copying took 94% of the time.

## Limits

- Only 3 to 5 short trials per condition, and the clock was not locked.
- Only five hardware counters could be recorded at once, so L2 and L3 hit rates are inferred from footprint rather than counted.
- The SSD tests used 2 GiB of a partly full system drive, so we did not measure full-drive steady state.

AI tools were used heavily; see [AI-USE.md](docs/AI-USE.md).

## Reproduction

Everything below regenerates the reports from the raw data in the repo (Python 3, standard library only):

```text
python common/analyze_all.py
python project-1-simd/scripts/roofline.py --reuse
python common/finalize.py
python common/analyze-followup.py ryzen-20261014
python common/analyze-pmc.py ryzen-20261014
python project-1-simd/scripts/analyze_ext.py ryzen-20261014
python project-1-simd/scripts/roofline_measured.py ryzen-20261014
python project-1-simd/timer-overhead/run.py analyze
python project-2-memory/scripts/run_large_pages.py analyze ryzen-20261014
python common/analyze-ssd-extension.py ryzen-20261014
python project-1-simd/scripts/gpu_axpy.py analyze ryzen-20261014
python common/validate.py
python common/validate-followup.py ryzen-20261014
python common/refresh_manifest.py
```

New measurements need Windows with GCC and fio on PATH (plus admin rights for counters and CuPy for the GPU). Use a new session name:

```text
python common/collect-followup.py --session NEW
python common/collect-load.py NEW
python common/collect-ssd-followup.py NEW C:/path/to/fio.exe
python project-1-simd/scripts/run_ext.py NEW
python project-1-simd/scripts/run_ext_gather.py NEW
python common/collect-ssd-extension.py NEW C:/path/to/fio.exe
python common/collect-ssd-warm.py NEW C:/path/to/fio.exe
python project-1-simd/scripts/gpu_axpy.py collect NEW
./project-2-memory/scripts/collect-counters.ps1 -Profile Zen3      # admin PowerShell
```
