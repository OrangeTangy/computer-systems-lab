# How fast can a computer think, fetch, and remember?

### Three experiments in computer architecture — ECSE 4320/6320

**SIMD • Cache & DRAM • SSD storage**

![Three experiments: SIMD, memory and SSD](docs/overview.svg)

Imagine a computer is a child doing homework. Its CPU does the thinking. Its caches are supplies on the desk. RAM is a cupboard across the room. Its SSD is the bookshelf where things stay after bedtime.

Our goal is to discover what makes the computer wait, and to measure it fairly. We ask three questions:

1. **Can we do several pieces of math at once?** That is the SIMD project.
2. **Does it matter where our information is and how we ask for it?** That is the memory project.
3. **How many requests should we send to storage at once?** That is the SSD project.

> **Evidence status:** This repository contains executable experiments and real measurements for all three projects. It is not a claim of full-rubric completion: hardware cache/TLB counters are unavailable on the accessible WSL platform, Windows large-page allocation failed for missing privilege, and short SSD trials do not establish steady state. See the [rubric audit](docs/RUBRIC.md) before submission.

## Explore the projects

| Project | Read the explanation | Inspect the measured numbers |
|---|---|---|
| **1 · SIMD** | [Methods and interpretation](project-1-simd/README.md) | [Results](project-1-simd/RESULTS.md) |
| **2 · Memory** | [Methods and interpretation](project-2-memory/README.md) | [Contention and page locality](project-2-memory/EXTENDED-RESULTS.md) |
| **3 · SSD** | [Methods and interpretation](project-3-ssd/README.md) | [Results](project-3-ssd/RESULTS.md) |

## What we found

| Observation | In everyday language | What the evidence supports |
|---|---|---|
| Float32 AXPY: native SIMD speedup fell from **5.00×** at N=1,024 to **1.31×** at N=4,194,304 | A bigger handful helps less when you are waiting for supplies | Faster arithmetic does not guarantee equally faster end-to-end execution |
| Float32 dot product: native speedup was **0.84×** at N=1,024 | Trying the “faster” way can actually be slower | Ordered summation, instruction overhead and dependency chains matter |
| Memory write traffic: probe latency rose from about **113 ns** without workers to **366 ns** with six workers | More children using the cupboard make one child wait longer | Concurrent traffic affects observed memory latency |
| 16,384 pointer nodes: **5.73 ns** at 64 B spacing versus **141.78 ns** at 4 KiB spacing | Scattering supplies makes collecting them harder | Address layout matters; this alone cannot isolate TLB misses from cache conflicts |
| SSD queue sweep: maximum tested median **81,604 IOPS**, 90% threshold at **QD128** | More requests can help until the line gets too long | The curve is variable and high-QD points are a supplemental session; [see the actual table](project-3-ssd/RESULTS.md) |

The memory numbers above are from the extended September 14 suite. Earlier September 10 pilot data remains in Project 2 as a separate dataset; do not silently merge the sessions.

## Reproduce the work

The measured suite runs natively on Windows with **GCC 13.1.0**, Python 3, and **fio 3.42**. Python analysis uses only the standard library. Native Windows source is deliberate: virtualized measurements would describe a different platform.

```powershell
# Run from the repository root. Run suites sequentially.
python project-1-simd/scripts/run.py
python project-1-simd/scripts/roofline.py
python project-2-memory/scripts/run.py --profile pilot --cpu 0
python project-2-memory/scripts/run_extended.py
python project-3-ssd/scripts/run.py --fio C:/path/to/fio.exe
python project-3-ssd/scripts/extend_queue.py C:/path/to/fio.exe
python common/analyze_all.py
python common/finalize.py
python common/validate.py
```

**SSD writes:** The SSD runner creates one new, disposable 2 GiB file inside `project-3-ssd/scratch/`, refuses an existing target, checks free space, and removes that exact file on success. It never accepts a raw device or partition. These are real writes to the SSD. Run only when this test workload is appropriate and the machine is otherwise idle. If interrupted, inspect the scratch file before removing it; the next run intentionally refuses to overwrite it.

The new suite scripts overwrite their named result files when rerun. Preserve a copy or Git commit before collecting a different session. The original Project 2 pilot runner instead creates timestamped directories.

## Repository map

```text
common/                 hardware metadata, topology probe, analysis and SVG plotting
docs/                   hypotheses, rubric mapping, learning guide and AI disclosure
project-1-simd/          C kernels, build variants, raw trials, compiler evidence, plots
project-2-memory/        dependent chains, traffic generators, page-locality experiments
project-3-ssd/           file-only fio runner, saved configs, original fio JSON, plots
```

## How we kept ourselves honest

- Predictions were written [before the new suite](docs/hypotheses.md).
- SIMD output is checked against simple scalar calculations before timing.
- Memory chains are checked for the expected cycle and final result.
- SSD data correctness is checked with a separate fio CRC32C verification pass.
- Timed conditions are repeated three times and interleaved with a fixed random seed.
- Plots show medians and min/max variability. Three trials give limited uncertainty information; whiskers are not confidence intervals.
- Raw data, flags and configs are retained. Unsupported measurements are marked unavailable instead of entered as zero.
- CPU benchmarks are pinned, but the Balanced power policy and background OS activity remain part of the environment. No exclusive core isolation is claimed.

## The deeper explanation — start here after the pictures

### Project 1: one instruction, several numbers

SIMD means **Single Instruction, Multiple Data**. Imagine putting eight toy cars into eight boxes with one movement. A vector instruction can apply the same operation to several numbers.

We compare a scalar build, a normal optimized build and a CPU-targeted build. They run the same algorithms and use the same input data. The independent multiply and AXPY loops give the compiler opportunities to use wider instructions. The dot product adds a complication: the answer depends on how additions are ordered, and floating-point addition is not perfectly associative.

We change the array size to move from nearby cache storage toward DRAM; shift starting addresses; include leftovers that do not fill a vector; skip elements with larger strides; and compare 32-bit and 64-bit numbers. Each experiment changes a specific property rather than changing everything at once.

**What we learned:** wider math helps most when arithmetic is an important part of execution time. Once data movement dominates, more arithmetic capacity cannot remove the wait. The [roofline discussion](project-1-simd/README.md#roofline-interpretation) puts units on that idea. Compiler reports and disassembly matter because a compiler flag is not proof that every loop vectorized.

### Project 2: nearby supplies, distant supplies, and crowded queues

Caches keep recently used information near the CPU. They are small and fast. DRAM holds more but takes longer to reach. We vary the working set to find when nearby storage no longer handles most requests.

To measure latency, the next address depends on the previous load: “open this box to find the address of the next box.” The CPU cannot issue all demand loads ahead of time. A predictable chain can still help prefetchers, so we also randomize the chain.

To study throughput, background workers make independent memory accesses. More workers can overlap requests. A separate dependent-load probe measures how the memory system feels under that traffic. The probe and workers are different request populations, so their bandwidth and latency must not be combined into an exact count of worker requests in flight.

Page translation adds another layer. The CPU uses a TLB to remember recent address translations. Widely separated pages can need more translations, but spacing by exactly 4 KiB can also create cache conflicts. Our timing results show a layout effect; missing hardware counters prevent a definitive TLB-miss attribution.

**What we learned:** latency, bandwidth, locality and concurrency describe different things. “Memory speed” is not one number. We also learned to keep an unexplained result visible rather than label every jump a cache boundary.

### Project 3: a librarian handling storage requests

The SSD is like a librarian. Sending one request and waiting gives a simple latency baseline. Sending several requests lets the librarian organize work and use several resources at once. Sending too many can create a long queue.

We use fio to control request size, sequential or random addresses, read/write mix and queue depth. For each run we collect throughput and latency together. We also inspect the distribution of achieved queue depth: requesting QD64 is not proof that the engine actually maintained it.

The average wait does not describe everyone's experience. A **p99 latency** means approximately 99% of measured requests finished within that time; the slowest 1% took longer. We retain p50, p95, p99 and p99.9 so the long waits remain visible.

Direct I/O avoids the Windows file cache on the tested path, but it does not disable the SSD's own caches or prove power-loss durability. The file occupies a limited range on the active system SSD. Short tests can capture bursts, background activity, garbage collection and device caching. We explicitly avoid claiming the device reached steady state or exhausted its SLC cache.

**What we learned:** throughput and responsiveness must be considered together. A high peak score is only meaningful when the workload, queue depth, duration, device state and latency distribution are stated.

### Two equations worth understanding

**Little's Law:** average requests in the system = completed requests per second × average time in the system. Use matching units and the same request population. SSD fio totals permit a same-run estimate; a separate memory probe is not an exact substitute for traffic-generator latency.

**AMAT:** average memory access time = hit time + miss probability × additional miss penalty. For several cache levels, use conditional miss probabilities and consistent penalties. We explain this model; we do not invent missing PMU miss rates to produce a numerical result.

## Learning and attribution

Try the [explain-it-yourself questions](docs/LEARNING.md). Read the [AI-use disclosure](docs/AI-USE.md) and add only independent work you actually perform. These experiments measure this laptop; they are not measurements of Tenstorrent accelerators or Micron DRAM chip internals.
