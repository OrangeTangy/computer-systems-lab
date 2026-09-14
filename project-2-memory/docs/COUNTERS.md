# Collecting missing hardware evidence

Current evidence: `../../common/wsl-counter-availability.txt` has no CPU PMU; `../../common/windows-pmc-sources.txt` lists native Windows cache/cycle sources. Enumeration is not a successful counter measurement. The current process is not elevated. No system security or hypervisor setting was changed.

The supplied profile was attempted using `wpr -start project-2-memory/docs/counters.wprp!LabCounters -filemode`. Windows returned **0x80070005, Access is denied**. WPR remained stopped. The original output is retained in `../../common/wpr-capture-attempt.txt`. This is a confirmed native capture-permission failure, not just an assumption based on WSL.

## Native Linux option

On a suitable Linux machine, first run `perf list` and confirm supported events and permissions. Build `src/membench.c` with GCC. Example only, to be adapted to actual available events:

```sh
gcc -O3 -std=c11 -Wall -Wextra src/membench.c -o membench
perf stat -r 5 -e cycles,instructions,cache-references,cache-misses \
  ./membench latency 67108864 64 random 100 5 0 4320
perf stat -r 5 -e dTLB-loads,dTLB-load-misses \
  ./membench latency 67108864 1024 random 100 5 0 4320
```

CPU 0 is an example; choose a permitted logical CPU and verify its type. Generic event availability and semantics differ. Record multiplexing/running percentages and keep groups small. Unsupported events are unavailable, not zero.

Whole-process `perf stat` includes setup and validation, whereas the internal timer does not. Use long runs, quantify setup overhead, or implement region-scoped counters before calculating precise miss rates for the timed loop. Compare small/large footprints and matched-node page locality. Keep pattern, seed, CPU and repetitions consistent.

## Native Windows option

Microsoft documents WPR hardware-counter capture in [Recording PMU Events](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/recording-pmu-events). Use an appropriately privileged session and verify that an actual trace contains nonzero, attributable events for the benchmark. Saved `counters.wprp` requests strict LLC-miss/instruction/cycle event counting at context switches; it is a starting profile, not a finished measurement.

TLB events may need model-specific definitions. Do not guess event encodings from another CPU family. Export per-process or timed-region data from a compatible trace analyzer, retain the original ETL, and document exact attribution and filtering. Samples are not automatically exact miss counts.

No uncollected counter value appears in the report. Completing these experiments is necessary for the Project 2 cache/TLB rubric requirement.
