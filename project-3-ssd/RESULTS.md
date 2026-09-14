# SSD measured results

135 trials. Three-second measurement windows after one-second ramp; short-run results, not steady-state certification.

## QD=1 baselines

| Pattern | KiB | IOPS | MB/s | Mean us | p50 us | p95 us | p99 us | p99.9 us |
|---|---|---|---|---|---|---|---|---|
| randread | 4 | 8428.62 | 34.52 | 117.49 | 72.19 | 177.15 | 382.98 | 5603.33 |
| randwrite | 4 | 11442.85 | 46.87 | 85.07 | 54.53 | 116.22 | 342.02 | 6062.08 |
| read | 128 | 942.35 | 123.52 | 1058.19 | 684.03 | 3063.81 | 7241.73 | 14483.46 |
| write | 128 | 510.5 | 66.91 | 1942.54 | 1417.22 | 7241.73 | 8978.43 | 16908.29 |

## Queue depth and tails

| QD | IOPS | Mean us | p99 us | p99.9 us | IOPS * mean seconds |
|---|---|---|---|---|---|
| 1 | 5418 | 182.21 | 2408.45 | 6717.44 | 0.99 |
| 2 | 9055 | 211.28 | 806.91 | 6324.22 | 1.96 |
| 4 | 17474 | 223.28 | 514.05 | 2023.42 | 3.9 |
| 8 | 23664 | 324.64 | 929.79 | 3850.24 | 7.76 |
| 16 | 10407 | 1520.75 | 7045.12 | 9109.5 | 15.8 |
| 32 | 17173 | 1844.78 | 7438.34 | 9502.72 | 31.56 |
| 64 | 33754 | 1862.29 | 7503.87 | 11075.58 | 62.14 |
| 128 | 79846 | 1049.99 | 3424.26 | 5406.72 | 83.84 |
| 256 | 81604 | 1821.69 | 4685.82 | 6455.3 | 148.66 |

Operational knee: first tested QD reaching 90% of maximum observed median IOPS = 128. This is a sampled range criterion, not proof of device saturation.

| QD | p50 us | p95 us | p99 us | p99.9 us |
|---|---|---|---|---|
| 8 | 264.19 | 528.38 | 929.79 | 3850.24 |
| 128 | 937.98 | 2023.42 | 3424.26 | 5406.72 |

## Achieved depth: median percentage per fio depth bucket

| Requested QD | Distribution |
|---|---|
| 1 | 1: 100.0%, 2: 0.0%, 4: 0.0%, 8: 0.0%, 16: 0.0%, 32: 0.0%, >=64: 0.0% |
| 8 | 1: 0.1%, 2: 0.4%, 4: 32.3%, 8: 67.3%, 16: 0.0%, 32: 0.0%, >=64: 0.0% |
| 32 | 1: 0.0%, 2: 0.0%, 4: 0.1%, 8: 0.4%, 16: 51.9%, 32: 48.1%, >=64: 0.0% |
| 64 | 1: 0.0%, 2: 0.0%, 4: 0.1%, 8: 0.1%, 16: 2.6%, 32: 73.8%, >=64: 23.3% |
| 128 | 1: 0.0%, 2: 0.1%, 4: 0.1%, 8: 0.3%, 16: 3.8%, 32: 21.5%, >=64: 74.2% |
| 256 | 1: 0.0%, 2: 0.0%, 4: 0.1%, 8: 0.2%, 16: 1.8%, 32: 9.2%, >=64: 88.9% |

## Read/write mixes: random 4 KiB, QD8

| Read % | IOPS | MB/s | Mean us |
|---|---|---|---|
| 0 | 12251.92 | 50.19 | 648.77 |
| 50 | 9364.3 | 38.37 | 840.78 |
| 70 | 30764.57 | 126.02 | 252.49 |
| 100 | 15195.34 | 62.25 | 518.89 |

## Block size: QD8

| Pattern | KiB | MB/s | Mean us |
|---|---|---|---|
| read | 4 | 26.74 | 1204.62 |
| read | 16 | 133.38 | 973.1 |
| read | 32 | 215.9 | 1206.6 |
| read | 64 | 602.03 | 864.33 |
| read | 128 | 302.11 | 3465.11 |
| read | 256 | 442.17 | 4739.33 |
| write | 4 | 47.47 | 685.93 |
| write | 16 | 71.24 | 1834.87 |
| write | 32 | 63.75 | 4107.01 |
| write | 64 | 35.31 | 14853.7 |
| write | 128 | 60.71 | 17301.72 |
| write | 256 | 49.27 | 42676.75 |
| randread | 4 | 109.17 | 293.88 |
| randread | 16 | 132.76 | 982.27 |
| randread | 32 | 172.65 | 1510.56 |
| randread | 64 | 252.88 | 2066.8 |
| randread | 128 | 335.8 | 3116.39 |
| randread | 256 | 349.76 | 5993.19 |
| randwrite | 4 | 46.14 | 702.25 |
| randwrite | 16 | 54.03 | 2419.94 |
| randwrite | 32 | 51.42 | 5098.21 |
| randwrite | 64 | 41.77 | 12566.35 |
| randwrite | 128 | 36.45 | 28824.45 |
| randwrite | 256 | 51.5 | 40928.17 |

## File range and buffered-I/O pitfall

| Study | Range MiB | Direct | IOPS | Mean us |
|---|---|---|---|---|
| range | 64 | 1 | 40716 | 177.3 |
| range | 2048 | 1 | 28271 | 273.97 |
| pitfall | 64 | 0 | 110352 | 45.4 |
| pitfall | 64 | 1 | 33714 | 218.86 |
## Interpretation and variability

The tested-range maximum median is 81,604 IOPS. The 90% operational threshold first occurs at QD128. QD128/256 were collected as a follow-up after a new file prefill, so a change at that boundary can reflect device-state drift as well as queue depth. A noisy or non-monotonic curve is not a clean saturation proof.

For the 64 MiB pitfall comparison, direct=0 produced a median 110,352 IOPS and 45.40 us mean latency. OS caching changes what the experiment measures; a performance increase is not guaranteed for every access pattern or run.
For the 64 MiB pitfall comparison, direct=1 produced a median 33,714 IOPS and 218.86 us mean latency. OS caching changes what the experiment measures; a performance increase is not guaranteed for every access pattern or run.

Three repetitions show variation but do not robustly characterize rare events or steady state. The nearly full, active system SSD and short time windows are material limitations. Completion latency includes the host/engine path and is not raw NAND access time.

The one-second write-bandwidth samples ranged from 57.06 to 208.50 MB/s over this short observation. No temperature or SLC-exhaustion evidence is available. The log alone cannot identify the cause of rate changes.