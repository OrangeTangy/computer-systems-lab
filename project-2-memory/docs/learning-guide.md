# Learning guide: measuring the memory hierarchy

## 1. Two loops, two questions

`p = next[p]` asks how long a load takes when the next address is unavailable until the previous result arrives. A single chain suppresses overlap of demand loads. Randomizing the chain makes prediction harder; it does not magically eliminate every prefetch or translation effect.

`sum += array[i]` lets the CPU discover many independent addresses ahead of time. It can overlap requests. Dividing its runtime by the number of loads gives amortized cost per element, not one-request memory latency.

Before looking at a plot, explain why ten overlapping 100 ns requests could finish much sooner than ten dependent 100 ns requests.

## 2. Working set and cache lines

At stride 64 B, this benchmark reads one 8-byte pointer from each selected 64 B region. Assuming a verified 64 B cache line, it uses only 1/8 of each fetched line's data. At stride 1024 B, it also skips entire lines. A 64 MiB allocated buffer therefore does not necessarily occupy 64 MiB of cache.

The footprint affects page translations too. A large random-access latency increase is not sufficient proof of a DRAM-only cost.

Checkpoint: if 16,384 nodes each occupy a different 64 B line, how much cache-line storage is touched? Answer: 1 MiB, even if the allocation spans 16 MiB at 1024 B stride.

## 3. Throughput versus latency

Illustrative numbers only: 20 GB/s at 100 ns corresponds to 2,000 bytes in flight by Little's Law. At 64 useful bytes per request, that is about 31.25 requests on average. This calculation only applies when bandwidth and latency describe the same request population and byte definition.

As load rises, requests overlap and throughput grows. Once a resource saturates, extra requests mostly wait. That is why a throughput-latency curve can flatten horizontally while latency continues increasing.

## 4. Average memory access time

For a simple two-level model: AMAT = L1 hit time + L1 miss probability * additional miss penalty. For more levels, use conditional miss probabilities for each successive cache and consistent incremental penalties. Do not multiply a global LLC miss rate by every level's miss rate or mix local and global rates.

Hardware counters help test explanations, but event semantics matter. A retired-load miss event, an LLC request event and a memory-controller transaction count need not count the same things.

## 5. First result to explain yourself

Open the latency plot and identify where sequential and random curves diverge. State the observation with numbers first. Then offer prefetching as a hypothesis and identify what else could explain it. Explain why timing a small repeatedly reused array would be misleading if advertised as DRAM bandwidth.

## Suggested learning sessions

1. Read `chase()` and trace a four-node cycle on paper. Understand validation before measuring.
2. Run the pilot, explain one plot, and inspect the raw JSON for a plotted point.
3. Verify the final machine topology and reproduce cache transitions with controlled trials.
4. Run loaded latency and explain the knee with Little's Law.
5. Gather cache/TLB evidence and write a report that separates observations from hypotheses.
