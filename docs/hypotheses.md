# Hypotheses recorded before the September 14 experiment suite

Project 1: independent elementwise multiply and out-of-place AXPY should auto-vectorize; strict ordered dot-product reduction may fail to vectorize. SIMD speedups should compress at large footprints. Misalignment and tails should matter more in short loops; stride should reduce useful bandwidth. Float32 can fit twice as many elements per vector as float64, but speedup need not double.

Project 2: random dependent loads should reveal latency transitions more reliably than predictable chains. More background memory traffic should eventually add queueing with little extra useful throughput. Spreading the same node count over more pages should increase translation pressure. Base-page versus huge-page conclusions require verified mappings and counter support. Existing September 10 pilot hypotheses are preserved in project-2-memory/docs/hypotheses.md.

Project 3: increasing queue depth should raise throughput until a knee; beyond it latency should rise faster than throughput. Large sequential blocks should deliver higher byte throughput than random 4 KiB requests. Mixed writes may worsen tail latency. Short runs may capture burst/cache behavior rather than steady-state device performance. Buffered I/O can yield misleading storage measurements.

All predictions are hypotheses, not promised results. Preserve anomalies and describe measurement limitations.
