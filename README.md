# ECSE 4320/6320 class-wide projects

Our three projects for Advanced Computer Systems:

1. **SIMD advantage profiling**: how much faster vector instructions make simple loops, and when they stop helping.
2. **Cache and memory profiling**: latency and bandwidth at each level of the memory hierarchy, and what happens under load.
3. **SSD profiling**: how block size, read/write mix and queue depth affect throughput and latency.

**Start with [REPORT.md](REPORT.md)**. It has the method, the main findings for each project and how to reproduce everything. [docs/OCTOBER-AUDIT.md](docs/OCTOBER-AUDIT.md) maps each rubric item to where it is covered, and [docs/AI-USE.md](docs/AI-USE.md) describes how AI tools were used.

## Machines

We measured on two machines and never mixed their results:

- **Intel i5-1240P laptop**: the first round, stored in the `project-*` folders.
- **AMD Ryzen 5 5500 desktop** (ADATA SU650 SATA SSD, GTX 1660 Ti): the second, fuller round, stored in `sessions/ryzen-20261014/`. This includes the hardware-counter, large-page, SSD device-state and GPU results.

## Layout

```text
REPORT.md              submission report (start here)
common/                shared collection, analysis, plotting and validation scripts
docs/                  hypotheses, rubric audit, AI-use note
project-1-simd/        SIMD kernels, build/run scripts, Intel results, timer-overhead study
project-2-memory/      memory benchmark, run scripts, Intel results, counter capture script
project-3-ssd/         fio runner and configs, Intel results
sessions/ryzen-20261014/  Ryzen data, figures and reports
```

Each results folder keeps the raw data (JSON / JSON Lines / fio output), the processed summaries, the figures and the scripts that made them.

## Running it

Requirements: Windows, Python 3, GCC (we used GCC 13.1 and 16.2) and fio 3.42+.

To regenerate all reports and figures from the saved data, without running any benchmarks, use the commands listed in [REPORT.md](REPORT.md#reproduction). To check the saved data:

```text
python common/validate.py
python common/validate-followup.py ryzen-20261014
```

The SSD scripts only write to new temporary files inside the repo's `scratch/` folders, check free space first and delete the files afterwards. They never touch a raw disk. They do perform real writes, so run them when the machine is otherwise idle.
