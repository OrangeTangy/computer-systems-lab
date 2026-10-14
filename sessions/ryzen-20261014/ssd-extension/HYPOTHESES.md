# Predictions before the SSD extension (written before collection)

- **Block size:** IOPS should fall and MB/s rise with block size until the SATA 6 Gb/s link (~550 MB/s usable) caps sequential and large random reads. Random and sequential reads should converge at large blocks because each request already covers many flash pages. Latency should grow roughly with transfer time once bandwidth-bound.
- **Read/write mix:** 4 KiB random writes land in the SLC cache and may complete faster than reads at low depth, but mixed traffic should reduce total IOPS below either pure case because reads queue behind program operations.
- **Data pattern:** the drive is not expected to compress data in its controller, so compressible and incompressible buffers should perform the same within noise. A difference would point to controller compression or a measurement artifact.
- **Buffered vs direct:** a buffered random read over a 2 GiB file that fits in 16 GiB of RAM should report far higher IOPS and microsecond latencies because it measures the OS page cache, not the SSD.
- **Sustained write:** throughput should start near the SATA ceiling while the SLC cache absorbs writes, then drop sharply (a cliff) once the cache fills, with tail latency rising. A short idle period should partially restore burst throughput as the drive folds SLC data into TLC in the background.
