# Validation evidence and open anomaly

GCC 13.1.0 compiled the native Windows benchmark with `-O3 -std=c11 -Wall -Wextra -fno-lto` without warnings. The initial smoke run contains 38 passing executions; the initial pilot contains 510 passing executions over 170 conditions (three trials each).

`scripts/verify.py` independently reconstructs the randomized chain in Python and checks the final returned offset. It also checks read checksums, time/throughput unit calculations, affinity status and rejection of an unsupported random-bandwidth request. The C benchmark additionally checks every selected node is visited once and validates initial writes against expected values.

Targeted `objdump -d` inspection of the pilot executable showed this dependency in `chase`:

```text
mov (%rcx,%rax,1),%rax
```

The next load address uses the previous load result in RAX. Calls to `chase` and `stream` remain inside the timed repetition loop, and their results are stored to the volatile sink. The stream loop retains both load and store instructions, plus modulo/mix branch overhead. This rules out a removed benchmark loop but does not establish peak memory bandwidth.

## Anomaly to investigate

At 64 B stride, the pilot random-chain median jumps from 7.87 ns at 1 MiB to 135.51 ns at 4 MiB. Do not automatically label this an LLC capacity boundary. The actual available cache capacity, selected CPU core type, translation behavior, background contention and effective frequency have not been established. Repeat a denser sweep around this region on the controlled final platform, verify cache sharing/topology, and collect relevant cache/TLB counters. Retain the original pilot data.

The 64 MiB sequential-chain median is 6.72 ns/load versus 159.67 ns/load for the random chain. This is evidence that the access pattern strongly changes measured cost; prefetching is a plausible explanation requiring supporting checks. The sequential value must not be described as intrinsic DRAM latency.
