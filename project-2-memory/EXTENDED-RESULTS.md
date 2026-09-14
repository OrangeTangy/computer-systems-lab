# Extended memory results

90 validated trials; three per condition.

| Read % | Load workers | Useful GB/s | Probe ns/load |
|---|---|---|---|
| 0 | 0 | 0.0 | 112.72 |
| 0 | 1 | 11.289 | 159.76 |
| 0 | 2 | 16.731 | 201.47 |
| 0 | 4 | 25.513 | 286.17 |
| 0 | 6 | 31.072 | 366.25 |
| 50 | 0 | 0.0 | 113.19 |
| 50 | 1 | 7.328 | 175.2 |
| 50 | 2 | 15.337 | 181.91 |
| 50 | 4 | 18.661 | 223.98 |
| 50 | 6 | 20.272 | 251.66 |
| 70 | 0 | 0.0 | 114.44 |
| 70 | 1 | 9.3 | 143.53 |
| 70 | 2 | 14.994 | 182.97 |
| 70 | 4 | 17.31 | 241.99 |
| 70 | 6 | 20.578 | 266.61 |
| 100 | 0 | 0.0 | 114.92 |
| 100 | 1 | 9.674 | 121.55 |
| 100 | 2 | 18.268 | 137.65 |
| 100 | 4 | 30.231 | 154.19 |
| 100 | 6 | 38.902 | 145.8 |

## Page locality

| Nodes | 64 B spacing ns | 4096 B spacing ns |
|---|---|---|
| 256 | 1.39 | 5.84 |
| 1024 | 3.99 | 20.67 |
| 4096 | 4.84 | 62.97 |
| 16384 | 5.73 | 141.78 |
| 65536 | 33.93 | 129.21 |

Page spacing alone does not prove TLB misses: cache-set conflicts and allocation footprint also change. Hardware counters are unavailable in this WSL instance.