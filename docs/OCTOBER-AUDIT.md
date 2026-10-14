# Rubric audit — current (October 14 revision)

This maps every requirement in the assignment to the evidence that addresses it. Point values are the assignment's category weights (110 + 185 + 185 = 480), not predicted scores. Older audits ([RUBRIC.md](archive/RUBRIC.md), [SUBMISSION-GATES.md](archive/SUBMISSION-GATES.md)) are kept in `docs/archive/` for history; where they say a counter or study is missing, this page supersedes them.

Main evidence for the Ryzen 5 5500 host: [session report](../sessions/ryzen-20261014/REPORT.md), [hardware counters](../sessions/ryzen-20261014/COUNTERS.md), [SIMD extension](../sessions/ryzen-20261014/SIMD-EXTENSION.md), [SSD extension](../sessions/ryzen-20261014/SSD-EXTENSION.md), [optional GPU](../sessions/ryzen-20261014/GPU.md). The original Intel i5-1240P studies remain in the project folders as a separate session.

## Common requirements

| # | Requirement | Evidence |
|---|---|---|
| 1 | AI-use note | [AI-USE.md](AI-USE.md): both tools, what each generated, what was checked or rejected. **Student section still to be filled in.** |
| 2 | Reproducible repository | Sources, build/run/plot scripts, raw JSON/JSONL, fio configs and raw output, processed data, figures, READMEs; [reproduction commands](../REPORT.md#reproduction) |
| 3 | Pre-experiment hypotheses | `HYPOTHESES.md` written before each collection: [main](../sessions/ryzen-20261014/HYPOTHESES.md), [SSD QD](../sessions/ryzen-20261014/ssd/HYPOTHESES.md), [SIMD ext.](../sessions/ryzen-20261014/simd-extension/HYPOTHESES.md), [SSD ext.](../sessions/ryzen-20261014/ssd-extension/HYPOTHESES.md), [GPU](../sessions/ryzen-20261014/gpu/HYPOTHESES.md); [original](hypotheses.md) |
| 4 | Correctness validation | SIMD: every run vs a double-precision reference (int32 exact); memory: chains verified as single cycles; SSD: CRC32C verification pass; GPU: bit-exact vs NumPy; `validate*.py` check matrices, units and hashes |
| 5 | Measurement discipline | Hardware/OS/compiler/fio versions, flags, topology, power policy, SMT state, CPU0 pinning in `environment.json`/`builds.json`; **measured core clock 4.22 GHz** from PMCs; 3–5 repetitions with min/max whiskers |
| 6 | Negative/failure case | SIMD: ordered dot (0.86x), float64 AVX2 AXPY slower than scalar from DRAM with 11x more demand DRAM fills, gather loop; memory: predictable-chain pitfall; SSD: buffered vs direct, SLC-cache burst vs sustained; GPU: end-to-end loses to CPU |
| 7 | Honest anomalies | Early 4–8 MiB latency rise; DRAM-fill rate above the capacity model; residual TLB/set-conflict confound; noisy SSD high-QD points — all retained with hypotheses |

## Project 1 — SIMD (110)

| Category | Pts | Evidence |
|---|---:|---|
| Baseline, correctness, reproducibility | 15 | 840-run main matrix + extension; reference checks; source snapshots and SHA-256; documented environment |
| Vectorization verification | 15 | Compiler reports (32-byte main loops, 16-byte epilogues), disassembly, **PMC instruction counts: 7.07 → 0.85 instructions/element (8.3x) for float32 AXPY**; FMA contraction off; gather study distinguishes GCC's emulated gather from forced hardware `vgatherdps` by disassembly |
| Locality and memory-bound analysis | 20 | Size sweeps across L1/L2/L3/DRAM with cache markers; **measured cycles/element 0.27 in L1 vs 2.73 from DRAM, IPC 3.1 → 0.29** |
| Alignment, tail, stride/gather | 20 | **[Timer-overhead sub-study](../project-1-simd/timer-overhead/README.md): the per-repetition clock read (21 ns) hides a 3x AVX2 speedup at N=16 and understates the in-cache speedup (6.7x batched vs 4.0x per-rep at N=1,024), so only the 65K rows resolve alignment/tail costs**; aligned/shifted × divisible/remainder tables; stride 1/2/4/8; **gather with identity vs random index** and a no-gather control |
| Roofline and quantitative insight | 20 | **[Measured roofline](../sessions/ryzen-20261014/ROOFLINE.md) with kernel points, measured roofs and a compute roof at the measured clock; dot product shown latency-bound (same GFLOP/s in L1 and DRAM, 3.3 cycles/add)**; traffic-matched two-read/one-write bandwidth reference; consistent useful-byte intensity; **compute ceiling from measured clock (4.22 GHz)**; store-port bound; stencil at 0.625 FLOP/B vs AXPY 1/6; bandwidth cross-check (18.6 GB/s from counters vs 16–18 GB/s reference) |
| AI transparency and failure case | 10 | AI note; ordered dot, float64 DRAM slowdown explained by counters, gather |
| Report quality | 10 | Tables with units and ranges, figures, limits sections |

Data types: float32/float64 throughout, **int32 added** in the extension. Kernels: AXPY, multiply, dot (main); **stencil** (extension).

## Project 2 — Cache and memory (185)

| Category | Pts | Evidence |
|---|---:|---|
| Zero-queue baselines | 25 | Dense dependent-chain sweep (210 runs); **cycles per load from PMCs: L1 4.2, L2 13.0, L3 region 58.5, DRAM ~508** with ns and GHz conversion |
| Pattern/granularity/RW sweeps | 35 | Sequential/random, 64/256/1024 B strides, 100/70/50/0% read mixes (Intel session); Ryzen loaded study for all four mixes |
| Throughput–latency knee | 35 | 0–5 physical-core workers × 4 mixes, 105 runs; 90%-of-max threshold at 2 workers; **Little's Law table: ≥34 lines in flight per streaming core, ~40 per core constant, ~228 total past the knee while bandwidth is flat**; population caveat kept |
| Working-set/cache/TLB analysis | 35 | **Measured L1/L2 DTLB misses and demand DRAM fills per load across footprints; AMAT-style fit (t_hit 53 cycles, DRAM+translation penalty 470 cycles); same-node page-spacing experiment isolating ~56–83 cycles per page walk** |
| Experimental rigor | 25 | CPU0 pinning, distinct physical cores for workers, five repetitions, timing-window lag/overhang measured, counter attribution bounds and zero event loss |
| AI transparency and pitfall | 15 | AI note; predictable-chain pitfall; timing-only TLB attribution rejected until counters existed |
| Report quality | 15 | Figures, tables, limitations |

**Huge pages:** [LARGE-PAGES.md](../sessions/ryzen-20261014/LARGE-PAGES.md) compares 4 KiB and 2 MiB pages for the same chains (2 MiB pages save 8–12% at 64–256 MiB and narrow the scattered-page gap), and shows the same study on a busy machine as an additional benchmark pitfall.

## Project 3 — SSD (185)

| Category | Pts | Evidence |
|---|---:|---|
| Safety and zero-queue baselines | 30 | Disposable files only, refuse-existing and free-space checks, exact-file deletion; direct I/O, aligned; four QD1 baselines with p50/p95/p99/p99.9 |
| Block-size and pattern sweeps | 35 | Intel: six sizes × patterns; **Ryzen: 4–256 KiB × random/sequential × read/write at QD32** |
| Read/write and queue-depth analysis | 40 | **QD1–256 in one interleaved session (knee QD64)**; Little's-Law L per run (equals QD to 16, lower beyond: achieved < requested depth); R/W mixes 100/70/50/0 on both drives; SATA NCQ depth (32) explains why deeper host queues add latency without throughput |
| Tail latency and device state | 25 | p50–p99.9 per run; **sustained 40 GiB write with 1 s logs (SLC cache), post-burst and after-idle recovery**; **temperature logged through a 30 GiB write (38 → 48 °C, full speed while hottest, r = +0.04): throttling excluded, slow phases are SLC exhaustion** |
| Reproducibility and data hygiene | 25 | Configs, raw JSON, indexes, seeds, processed JSON, scripts, repeated trials, environment |
| AI transparency and pitfall | 15 | Buffered vs direct on both drives; burst-vs-steady-state; requested vs achieved QD |
| Report quality | 15 | Figures, tables, limitations |

Data pattern: incompressible by default; **compressible vs incompressible** compared in the extension.

## Optional GPU extension

CPU vs GPU AXPY on a GTX 1660 Ti with kernel-only and end-to-end (pageable and pinned) times: [GPU.md](../sessions/ryzen-20261014/GPU.md). Not required for full credit.

## What the student still needs to do

1. Fill in the **Independent student work** section of [AI-USE.md](AI-USE.md) with checks you actually performed.
2. Be able to explain: why the ordered dot product does not speed up; useful bytes versus bus traffic; why probe latency and worker throughput cannot be combined in Little's Law; how the counter order was identified; why QD beyond 32 adds only latency on SATA; what the SLC-cache cliff means for every short write benchmark.
3. You granted "Lock pages in memory" to your account for the large-page study. You can remove it afterwards by restoring the policy you exported before the change (`secedit /configure /db C:\restore.sdb /cfg C:\secpol-backup.inf /areas USER_RIGHTS` in an Administrator shell, then sign out and in); the committed results do not depend on keeping it.
