# Project 2: Cache & Memory Performance Profiling

An ECSE 4320/6320 project and learning repository. Status: validated portable baseline and preliminary Windows pilot; final required experiments remain open. The assignment lists October 16 as the deadline.

## Start here

Read `docs/learning-guide.md`, then `docs/hypotheses.md` and `docs/experiment-plan.md`.

Requires Python 3 and GCC on PATH. No third-party Python packages are needed.

```text
python scripts/run.py --profile smoke --cpu 0
python scripts/run.py --profile pilot --cpu 0
python scripts/analyze.py
```

The runner builds with GCC, validates each run, pins to the requested logical CPU, randomizes condition order, and retains commands and raw observations. Choose an allowed CPU using the actual machine topology. CPU 0 is only the initial Windows pilot choice; its core type has not been verified.

`--profile full` expands the sweep to 256 MiB, seven repetitions and at least 0.3 s per trial. This is a fuller baseline sweep, NOT all assignment requirements. It can consume several minutes and up to roughly 600 MiB transiently when constructing dense pointer chains. Avoid running while other performance-sensitive jobs are active.

Optional `--seconds` and `--reps` override run duration and repetitions. Each run gets a new UTC directory. Analysis accepts an explicit raw run directory or defaults to the newest pilot.

## Repository layout

- `src/membench.c`: dependent pointer chase and scalar read/write streaming benchmark; Windows/Linux timing and affinity.
- `scripts/run.py`: build, environment capture, experiment scheduling, raw JSONL.
- `scripts/analyze.py`: processed JSON, observations, SVG plots with median/min-max variability.
- `data/raw/`: original trial records and environment snapshots.
- `data/processed/`: summaries derived from raw trials.
- `figures/`: standalone SVG plots.
- `docs/`: hypotheses, learning notes, requirement checklist, report outline and AI disclosure.

## What the numbers mean

Latency = elapsed ns / dependent loads. Bandwidth = useful 8-byte operations / second in GiB/s. These quantities describe different kernels: bandwidth ns/op is not single-request latency. No CPU-cycle estimates are reported because effective core frequency has not been measured. Timer ticks are not CPU cycles.

Allocation and first-touch happen before timing. Latency initialization constructs and validates a single cycle visiting every selected location. Warm-up traverses that cycle once. Returned indices and stream checksums are consumed to prevent dead-code removal; compiler barriers preserve repeated passes. Cached stores need not have reached DRAM at timer stop. The streaming kernel includes loop/mix overhead and is not a peak-bandwidth tool.

## Reproducibility limits

The Windows pilot does not control frequency, isolate the core, establish P/E-core mapping, collect PMU counters, or verify memory page backing. Hardware queries/WSL enumeration were partially blocked in this environment. Cache capacity boundaries and DRAM-only interpretations must wait for verified topology and a controlled final run.

The C implementation is intended for 64-bit GCC targets. Native Windows smoke/pilot execution is tested; Linux portability is provided but has not yet been executed. Do not claim Linux validation until it is run there.

## References

- Assignment: ECSE4320_6320_Class-wide_Projects.pdf, common requirements and Project #2 (pages 1, 4-5).
- Intel MLC: https://www.intel.com/content/www/us/en/developer/articles/tool/intelr-memory-latency-checker.html
- perf event availability: https://www.man7.org/linux/man-pages/man1/perf-list.1.html
- perf permissions: https://www.man7.org/linux/man-pages/man2/perf_event_open.2.html

See `docs/ai-use.md` for the AI disclosure. No data is synthetic.
