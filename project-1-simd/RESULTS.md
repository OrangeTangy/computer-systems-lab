# SIMD measured results

450 trials. Three trials per condition. CPU 0 pinned; Balanced power policy; background system activity uncontrolled.

| Type | Kernel | N | Native speedup | Native GFLOP/s |
|---|---|---|---|---|
| float | AXPY (out of place) | 1024 | 5.0 | 26.92 |
| float | AXPY (out of place) | 4194304 | 1.31 | 3.03 |
| float | Multiply | 1024 | 4.4 | 14.29 |
| float | Multiply | 4194304 | 1.14 | 1.6 |
| float | Dot product | 1024 | 0.84 | 3.08 |
| float | Dot product | 4194304 | 0.91 | 3.15 |
| double | AXPY (out of place) | 1024 | 2.72 | 16.36 |
| double | AXPY (out of place) | 4194304 | 1.01 | 1.64 |
| double | Multiply | 1024 | 3.73 | 9.77 |
| double | Multiply | 4194304 | 1.14 | 0.79 |
| double | Dot product | 1024 | 1.08 | 3.86 |
| double | Dot product | 4194304 | 0.97 | 2.17 |

## Alignment and tails

| Type | N | Offset (elements) | Scalar ns/element | Auto ns/element | Native ns/element |
|---|---|---|---|---|---|
| float | 16 | 0 | 1.724 | 1.585 | 1.803 |
| float | 16 | 1 | 1.941 | 1.561 | 1.595 |
| float | 19 | 0 | 1.696 | 1.399 | 1.406 |
| float | 19 | 1 | 1.585 | 1.438 | 1.385 |
| float | 65536 | 0 | 0.353 | 0.108 | 0.102 |
| float | 65536 | 1 | 0.429 | 0.15 | 0.117 |
| float | 65539 | 0 | 0.332 | 0.11 | 0.094 |
| float | 65539 | 1 | 0.384 | 0.192 | 0.116 |
| double | 16 | 0 | 2.187 | 2.069 | 1.536 |
| double | 16 | 1 | 1.848 | 2.211 | 1.57 |
| double | 19 | 0 | 1.806 | 1.406 | 1.369 |
| double | 19 | 1 | 1.407 | 1.438 | 1.464 |
| double | 65536 | 0 | 0.457 | 0.391 | 0.401 |
| double | 65536 | 1 | 0.459 | 0.429 | 0.392 |
| double | 65539 | 0 | 0.481 | 0.364 | 0.393 |
| double | 65539 | 1 | 0.457 | 0.407 | 0.422 |

## Stride study: multiply, N=524288

| Type | Stride | Scalar ns/element | Auto ns/element | Native ns/element |
|---|---|---|---|---|
| float | 1 | 0.4 | 0.244 | 0.26 |
| float | 2 | 0.881 | 0.895 | 0.919 |
| float | 4 | 2.123 | 2.151 | 2.075 |
| float | 8 | 4.791 | 4.785 | 5.012 |
| double | 1 | 0.847 | 0.981 | 0.705 |
| double | 2 | 2.212 | 2.182 | 2.824 |
| double | 4 | 4.884 | 4.618 | 5.589 |
| double | 8 | 10.58 | 9.304 | 9.565 |