# ECSE 4320/6320: SIMD, memory and SSD profiling

Three measured architecture studies on two machines, never pooled: the original **Intel i5-1240P laptop** session (GCC 13.1.0, fio 3.42) and the **AMD Ryzen 5 5500** session of October 14 (Windows 11, GCC 16.2.0, fio 3.43, ADATA SU650 SATA SSD, GTX 1660 Ti). The [rubric audit](docs/OCTOBER-AUDIT.md) maps every requirement to its evidence.

| Ryzen session report | Contents |
|---|---|
| [Main report](sessions/ryzen-20261014/REPORT.md) | SIMD matrix, cache/DRAM sweep, loaded-latency knee, SSD queue-depth curve and QD1 baselines |
| [Hardware counters](sessions/ryzen-20261014/COUNTERS.md) | Core cycles, instructions, L1/L2 DTLB misses, demand DRAM fills |
| [SIMD extension](sessions/ryzen-20261014/SIMD-EXTENSION.md) | int32, stencil, gather |
| [SSD extension](sessions/ryzen-20261014/SSD-EXTENSION.md) | Block size, R/W mix, data pattern, buffering, sustained-write device state |
| [GPU (optional)](sessions/ryzen-20261014/GPU.md) | CPU vs GPU, kernel-only vs end-to-end |

## Method

CPU benchmarks are single-threaded and pinned to CPU0 (load workers on distinct physical cores), with warm-up, deterministic data and a correctness check before timing: SIMD against a double-precision reference (int32 exact), pointer chains verified as one cycle, SSD files CRC32C-verified, GPU results bit-exact. Each condition is repeated 3–5 times in a fixed shuffled order; tables give median [min, max] and plots draw min–max whiskers (not confidence intervals). Predictions were written to `HYPOTHESES.md` before each collection. Hardware, OS, compiler and flags, topology, power policy and source hashes are stored with each session. Limits: SMT on, Balanced power policy, no exclusive core isolation. The core clock was nonetheless **measured at 4.22 GHz** during the runs by the cycle counter.

## 1. SIMD advantage profiling

**Kernels and builds.** AXPY, elementwise multiply, ordered dot (main matrix, 840 runs) plus `3x + y` in int32/float32/float64 and a three-point stencil (extension). Builds: scalar (`-fno-tree-vectorize`), default auto-vectorized (SSE2), and native (`-march=native`, AVX2), all `-O3 -ffp-contract=off`.

**Vectorization verified three ways:** compiler reports (32-byte main loops, 16-byte epilogues), disassembly, and **retired-instruction counts: float32 AXPY drops from 7.07 to 0.85 instructions per element (8.3x)**, matching 8 lanes per 256-bit instruction.

**Locality.** In L1 native float32 AXPY needs **0.27 core cycles/element versus 1.24 scalar (4.6x)**; from DRAM it needs 2.73 versus 3.07 (1.1x), and the native build's IPC falls from 3.1 to 0.29. The speedup compresses because the core is waiting for data. 2.73 cycles/element at 4.22 GHz is 18.6 GB/s of useful traffic, matching the separately measured two-read/one-write stream reference (16–18 GB/s). The scalar baseline runs at about 6 IPC in L1, the 6-wide dispatch limit, so in cache SIMD wins by issuing fewer instructions.

**Alignment, tails, stride, gather.** Shifted-by-one and remainder cases change native time by less than 10% at 65K elements; at 16–19 elements timer and call overhead dominate. Stride 2/4/8 multiplies time per useful element as cache-line utilization falls, and the vector advantage disappears by stride 4. The gather loop `x[idx[i]]` is the clearest negative case: GCC emits an emulated gather that gains only 1.4x even with a perfectly local index, a **forced hardware `vgatherdps` is slower than scalar code** on Zen 3, and with a random index over 64 MiB every build takes about 6–7 ns/element.

**Data types.** In L1 int32 and float32 run at the same speed (both 8 lanes) and float64 is 1.5x slower. From DRAM float64 takes 1.9x as long, close to its 2x bytes per element.

**Roofline.** Useful arithmetic intensity is 1/6 FLOP/B for AXPY, 1/12 for multiply and 0.625 for the stencil. With the measured clock, the FP32 ceiling is 32 FLOP/cycle x 4.22 GHz = **135 GFLOP/s** (two 256-bit FMA pipes). The memory roof uses the measured traffic-matched bandwidth. All three main kernels sit far left of the ridge point and are memory-bound out of cache. In L1 the AXPY limit is the store port (about 0.125 cycles/element), and the measured 0.27 reaches 46% of it. The stencil's higher intensity keeps 3.7x of SIMD benefit at N = 1,048,576 (L3-resident), where `3x + y` keeps 2.6x.

**Negative cases.** The ordered dot product (serial dependency) gains nothing and reaches 0.864x at the largest size. **Float64 AVX2 AXPY from DRAM is slower than scalar (6.56 versus 5.52 cycles/element) and incurs 11x more demand DRAM fills**: the wider loop outruns the hardware prefetcher.

## 2. Cache and memory

**Zero-queue baselines** (dependent random chain, cycles from the counter): **L1 4.2 cycles (0.99 ns), L2 13.0 (3.1 ns), 4 MiB/L3 region 58.5 (14.0 ns), 64 MiB/DRAM about 508 (122 ns)**. The L1 value matches Zen 3's documented 4-cycle load-to-use latency, which independently validates the timer.

**Working-set and TLB analysis with counters.** At 4 MiB, 0.77 L1-DTLB misses per load (1,024 pages against 64 entries) but no L2-DTLB misses and no DRAM fills: L3 data plus second-level TLB lookups. At 64 MiB, 0.97 DRAM fills and 0.62 page walks per load. An AMAT fit with the counted DRAM-fill rate gives a 53-cycle hit time and a 470-cycle DRAM-plus-translation penalty. **TLB impact:** the same 16,384 nodes spread over 16,384 pages instead of 256 raise L2-DTLB misses from 0.0008 to 0.66 per load and time from 43 to 98 cycles, about 56–83 cycles per page walk. **Huge pages** ([details](sessions/ryzen-20261014/LARGE-PAGES.md)): 2 MiB pages cut DRAM-region latency by 8–12% at 64–256 MiB (125 to 115 ns at 64 MiB), 13% at 4 MiB (L1-DTLB refills), and shrink the scattered-versus-packed gap from 13.9 to 9.2 ns. At least about a third of that gap is translation; the rest is 4 KiB cache-set aliasing, which large pages do not remove. 16 MiB shows no clear gain, an unexplained anomaly. The same study run on a busy machine reversed the 64 MiB result, a second benchmark pitfall.

**Pattern/granularity/RW and the knee.** The Intel session covers sequential versus random access, 64/256/1024 B strides and 100/70/50/0% read mixes. On the Ryzen host, a 64 MiB probe on CPU0 runs with 1–5 traffic workers on separate physical cores for each mix. All mixes reach 90% of their maximum throughput at **two workers** (for example 27.2 of 30.1 GB/s at 100% reads), while probe latency keeps rising (138 → 483 ns): beyond the knee, extra concurrency adds queueing delay, not bandwidth. Little's Law applies within one request population, so probe latency and worker throughput are not multiplied together.

**Pitfall.** A predictable (sequential) chain looks 30x faster than the random chain at 128 MiB (4.1 versus 136 ns) because prefetchers hide DRAM. It must not be reported as memory latency.

**Anomalies retained.** The random-chain rise begins around 4–8 MiB, below the 16 MiB L3, with large variance. The DRAM-fill rate at 64 MiB (0.97) exceeds the 0.75 a capacity-only model predicts; Zen 3's victim-cache L3 and page-table traffic are plausible causes.

## 3. SSD

**Safety.** Only new disposable files inside the repository's ignored `scratch/` folders, refused if they already exist, checked against free space, CRC32C-verified, and deleted by exact name afterwards. Never a raw device.

**QD1 baselines** (Ryzen, 5 trials, median): 4 KiB random read 168 us mean (p99 259 us); 4 KiB random write 63 us (p99 109); 128 KiB sequential read 310 us; 128 KiB sequential write 388 us. p50/p95/p99/p99.9 are in the report.

**Queue depth and Little's Law.** QD1–256 random 4 KiB reads in one interleaved session: IOPS rises from 6.9K (QD1) to 63K at **QD64, the first QD within 90% of the maximum**, while mean latency rises from 144 us to 2.6 ms at QD256. From QD32 to QD256, IOPS grows only 12% while latency grows about 6.5x: SATA NCQ holds 32 commands, so extra requests mostly wait in the host queue. L = IOPS x latency equals QD up to 16 but is only 24–80 at QD32–128, so fio did not keep every requested I/O outstanding. The same appears in two 4 KiB rows of the QD32 block-size study (L = 20–25): requested depth is not achieved depth.

**Block size, mix, data pattern.** Throughput rises from about 210 MB/s at 4 KiB to the 450–540 MB/s SATA ceiling from 16–32 KiB upward, and random and sequential reads converge. A 50/50 mix falls below both pure reads and pure writes, and read latency doubles in mixed traffic. Compressible data gives no reliable benefit: trial ranges overlap and are dominated by cache state.

**Device state and tails.** A 40 GiB sustained write shows a **sawtooth**: about 312 MB/s while the SLC cache absorbs writes (about 2 GiB per episode), then about 79 MB/s while it folds into TLC, 13 cycles in 255 s, with 58% of the time in the slow state. The same 79 MB/s appears as the minimum of many short write trials, so every short write result is a burst number. After 120 s idle a burst recovers to 312 MB/s from 201. Write p99 reaches 30–100 ms in cache-full runs. Temperature needs elevation and is recorded as unavailable.

**Misleading setups.** Buffered I/O on a cold file is 0.61x the direct IOPS (cache-manager overhead with no hits); on a warm file it is **5x** (measuring RAM). The original Intel session also contains a buffered/direct comparison and a file-range study.

## Optional GPU

On a GTX 1660 Ti, AXPY with data on the device runs at 237 GB/s, 14x the CPU's DRAM-limited rate, but end-to-end with PCIe copies it is 0.72x the CPU: copies are 94% of GPU-side time. Small N is launch-bound (about 12 us per launch).

## Reproduction

Python 3 (standard library) regenerates every analysis from the committed raw data:

```text
python common/analyze_all.py
python project-1-simd/scripts/roofline.py --reuse
python common/finalize.py
python common/analyze-followup.py ryzen-20261014
python common/analyze-pmc.py ryzen-20261014
python project-1-simd/scripts/analyze_ext.py ryzen-20261014
python common/analyze-ssd-extension.py ryzen-20261014
python project-1-simd/scripts/gpu_axpy.py analyze ryzen-20261014
python common/validate.py
python common/validate-followup.py ryzen-20261014
python common/refresh_manifest.py
```

New collections need native Windows with GCC/objdump on PATH, fio for the SSD studies, Administrator rights for the counter capture, and CuPy for the GPU. Use a new session name; every collector refuses an existing output directory:

```text
python common/collect-followup.py --session NEW
python common/collect-load.py NEW
python common/collect-ssd-followup.py NEW C:/path/to/fio.exe
python project-1-simd/scripts/run_ext.py NEW
python project-1-simd/scripts/run_ext_gather.py NEW
python common/collect-ssd-extension.py NEW C:/path/to/fio.exe
python common/collect-ssd-warm.py NEW C:/path/to/fio.exe
python project-1-simd/scripts/gpu_axpy.py collect NEW
./project-2-memory/scripts/collect-counters.ps1 -Profile Zen3      # Administrator PowerShell
gcc -O2 common/export-pmc.c -ladvapi32 -o export-pmc.exe; ./export-pmc.exe counters.etl > sessions/NEW/counters/pmc.csv
```

The load-study placement is configured for the six-core Ryzen host. Revise it for another processor.

## Limits

Three to five short trials per condition; min/max ranges are not confidence intervals. Five PMC events per capture: there is no L2/L3 miss counter, so cache-level residency is inferred from footprint. The SSD uses a 2 GiB range on a partly used system drive, so the full-device preconditioned steady state was not measured. Short-run SSD writes are burst results. See [AI-use disclosure](docs/AI-USE.md); the student must review and be able to explain the submission.
