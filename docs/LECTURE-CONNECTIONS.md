# How the three lecture decks explain our experiments

**For a seven-year-old:** Suppose you are making sandwiches. You can do a ready step while another step waits; put toppings on several sandwiches together; ask a friend to share your table; or use several tables. None of that helps if everyone is waiting for the same jar. Our computer experiments measure these different kinds of waiting.

These notes connect the user's supplied ECSE 4320/6320 lectures to the actual repository evidence. Page numbers below are PDF page numbers, starting at 1. The original PDFs and their artwork are not republished in this public repository. Numerical examples printed on slides are teaching examples, not measurements of this laptop.

| Source | Pages | Concepts used here |
|---|---|---|
| `Thread 1-1-1.pdf`, Part 1-1 | 2–9 | Dependencies, out-of-order execution, register renaming, hardware cost, iterative engineering |
| Same | 10–15 | Branch prediction, speculation, recovery and diminishing returns |
| Same | 17–21 | Superscalar issue, available ILP, dynamic versus compiler scheduling |
| `Thread 1-1-2.pdf`, Part 1-2 | 2–5 | Data parallelism and SIMD; lane count does not equal speedup |
| Same | 6–9 | SMT and latency hiding; throughput can improve while each thread slows |
| Same | 10–16 | Multicore execution, placement, shared resources, Amdahl's law and bottleneck selection |
| `Thread 1-1-3.pdf`, Part 1-3 | 2–4 | CPU/GPU optimization goals, SIMT and divergence |
| Same | 5–9 | Blocks, grid, placement, coalescing, reuse, occupancy and warp scheduling |
| Same | 10–11 | Workload suitability and data supply as a constraint |

## 1. Four kinds of parallelism are not interchangeable

| Kind | Simple picture | Technical meaning | What this repository measures |
|---|---|---|---|
| ILP | Do a ready sandwich step while another waits | Independent instructions from one instruction stream can overlap | Dot-product dependency evidence and independent array work; no direct scheduler-size measurement |
| SIMD | Put a topping on several sandwiches together | One vector instruction operates on several data elements | Project 1 scalar/default/native build comparisons |
| SMT | Two helpers share one table and tools | Hardware threads share a physical core's execution resources | Topology is recorded; the controlled memory run avoids SMT siblings, so it is **not** an SMT speedup experiment |
| Multicore | Several tables do work at once | Separate physical cores run different threads | Project 2 background workers contend for shared memory while a separate core probes latency |

Part 1-2 page 16 presents these categories together. A wide vector register is not another core; a second logical CPU is not necessarily another physical core. `common/core-masks.json` establishes the actual Windows core relationship: masks 3, 12, 48 and 192 each contain two logical CPUs. The controlled follow-up uses CPU 0 for the probe and CPUs 2, 4 and 6 for workers, one logical CPU from each distinct P-core.

## 2. True dependencies explain the dot-product result

Part 1-1 pages 3–8 separate true value dependencies from reuse of a register name. Register renaming can remove the latter, but it cannot make an unknown value available early. Out-of-order execution runs independent ready work while respecting real dependencies.

Our dot product contains `sum += x[i] * y[i]`. The next addition depends on the previous sum. In the strict-order native assembly, packed multiplication is followed by scalar additions and lane rearrangement. That is why “some SIMD instructions exist” does not prove a parallel reduction. Native float32 dot speedup was 0.84x at N=1,024 and 0.91x at N=4,194,304 in the retained session.

Using several accumulators could expose more ILP, but regrouping floating-point additions changes numerical semantics. It must be treated as an explicitly validated algorithmic variant, not silently compared under a different correctness contract. This also connects to Part 1-1 pages 20–21: compiler transformations and runtime hardware scheduling solve related but different problems.

**Evidence:** [targeted assembly](../project-1-simd/VECTOR-EVIDENCE.md), [measured SIMD tables](../project-1-simd/RESULTS.md).

## 3. Why eight lanes do not guarantee eight times the speed

Part 1-2 page 5 gives an eight-lane/2.7x teaching example. We did not reproduce or adopt that number. Our measured small-array float32 AXPY speedup was about 5.00x and large-array speedup about 1.31x.

Vector arithmetic accelerates only part of a program. Loads, stores, scalar tails, loop/control work, dependencies, and data supply can still take time. A scalar processor may already overlap independent instructions, so the comparison is not “one completely idle machine versus eight fully busy machines.” Misalignment and skipped elements can increase work per useful element. These are exactly why the project measures alignment, tails, stride and size instead of multiplying the lane count into a promised speedup.

**Evidence:** [size/alignment/stride results](../project-1-simd/RESULTS.md), [working-set plot](../project-1-simd/figures/float-0-locality.svg), [roofline model and its mismatch](../project-1-simd/ROOFLINE.md).

## 4. Amdahl's law makes the unchanged work visible

Part 1-2 page 14 gives `S = 1 / ((1-P) + P/N)`. Here P is the fraction of baseline execution time improved, and N is the ideal acceleration of that fraction. The remaining fraction does not improve.

Illustration only: if arithmetic were 80% of baseline time and became eight times faster, total speedup would be `1/(0.2+0.8/8) = 3.33x`, not 8x. If arithmetic were only 20%, the same ideal acceleration would yield `1/(0.8+0.2/8) = 1.21x`.

This provides a way to reason about compressed large-array SIMD gains. It does **not** identify the actual arithmetic fraction from our speedup alone: measured clocks, cache behavior, overlap and overhead can change too. The memory worker sweep also changes resource contention rather than simply dividing a fixed parallel fraction by N, so fitting a textbook Amdahl curve to it would overstate the model.

## 5. Prediction, speculation and prefetching need careful distinctions

Part 1-1 pages 10–15 discuss predicting control flow and recovering from wrong-path execution. Our predictable-versus-random pointer chain is primarily an **address-pattern** experiment. Better sequential timing is not a measurement of branch-predictor accuracy, and it is not proof of fewer branch mispredictions.

Similarly, the modulo-based read/write worker has control-flow and instruction overhead. Without branch counters, we cannot attribute all throughput differences to the memory bus. More elaborate CPU control hardware has area, power and verification costs, but this project measures runtime—not chip area, power or predictor complexity.

The practical lesson is to name the mechanism supported by the evidence, and preserve alternative explanations.

## 6. Hiding a wait is different from making the wait shorter

Part 1-2 pages 6–9 show how another hardware thread can use resources while one waits. Part 1-3 pages 8–9 describe the analogous GPU strategy of scheduling another ready warp. These mechanisms improve useful work during a wait; they need not reduce the latency of the original request.

Project 2 intentionally distinguishes a dependent-load probe from independent traffic generators. More traffic can increase total useful throughput while raising probe latency. Part 1-2 pages 10–12 also explain why multicore work must consider shared resources and placement. That motivated the [controlled P-core follow-up](../project-2-memory/CONTROLLED-RESULTS.md), which fixes placement and varies delay instead of mixing P/E cores as load grows.

Project 3 applies a related queueing idea at a different layer. Several outstanding SSD requests may improve device utilization; too many can add waiting. A fio queue-depth experiment is **not** a measurement of GPU occupancy, SMT, or an SSD controller's internal thread scheduler. It establishes a host-visible throughput/latency relationship.

## 7. GPU concepts: relevant interpretation, not invented GPU results

Part 1-3 distinguishes latency-oriented CPU design from throughput-oriented GPU execution. These are design tendencies, not absolute rules about every CPU/GPU workload.

- **SIMT:** the programmer describes threads, while groups share an instruction stream. It is not identical to explicitly writing one CPU SIMD instruction.
- **Divergence:** lanes in a group follow different paths, which can leave some inactive while another path runs. CPU branch misprediction and GPU divergence are different phenomena.
- **Grid and blocks:** a grid contains blocks, and a block groups threads for placement and cooperation. Block size affects resources and occupancy; it is not a synonym for core count.
- **Coalescing and reuse:** neighboring accesses can make data movement more efficient. Our CPU stride study illustrates the broader value of locality, but CPU cache lines and GPU memory transactions are not interchangeable measurements.
- **Occupancy:** resident warps can help hide latency when enough ready work exists. More occupancy is not automatically better after the limiting resource is saturated or when resource usage changes.

Our multiply/AXPY kernels offer regular data parallelism. A single dependent pointer chain exposes little usable parallelism, so simply moving it to a GPU would not remove its dependency. Graph processing can expose many independent tasks yet still suffer from divergence and irregular accesses; “graph traversal” is not automatically a favorable GPU workload.

No CUDA performance data is claimed. The assignment makes GPU/CUDA optional, so understanding these concepts does not require inventing an extension or substituting theoretical GPU numbers for CPU measurements. If later measured, report both kernel-only and transfer-inclusive time.

## 8. The lecture's engineering loop, applied to each project

Part 1-1 page 9 and Part 1-2 page 15 emphasize measuring, identifying a bottleneck, choosing a mechanism, evaluating costs, and measuring again.

| Step | SIMD | Memory | SSD |
|---|---|---|---|
| Workload and goal | Numeric kernels; reduce time per element | Access chains/streams; distinguish waits from throughput | File I/O; characterize throughput and response times |
| Initial evidence | Scalar/native timing and assembly | Size, pattern and loaded-latency plots | Same-run IOPS, mean latency and tails |
| Candidate bottleneck | Arithmetic, ordered reduction or data supply | Dependency, locality or shared-resource contention | Request serialization or saturation/queueing |
| Mechanism tested | Vector build, datatype and layout changes | Fixed-core traffic with varied offered load | Request size, pattern, mix and queue depth |
| Costs/tradeoffs | Tail/control overhead; numerical ordering | More contention; cache/TLB attribution uncertainty | Longer tails, finite-run effects and active-drive state |
| Re-measure and limit claim | Keep slower dot and weak large-N gains | Preserve old run; quantify improved timing alignment | Keep noise and label supplemental high-QD session |

This loop is the organizing principle of the report. It improves the explanation; it does not replace missing hardware evidence or independently demonstrated student understanding.
