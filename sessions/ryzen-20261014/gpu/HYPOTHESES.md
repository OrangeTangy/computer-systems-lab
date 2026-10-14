# Predictions before the GPU extension (written before collection)

- **Kernel-only:** AXPY moves 12 bytes per 2 FLOPs, so the GPU kernel should be memory-bound and approach a large fraction of the 1660 Ti's 288 GB/s at large N, roughly 10x the CPU's ~18 GB/s DRAM stream. At small N a fixed launch overhead of several microseconds should make the GPU slower than the in-cache CPU.
- **End-to-end:** every element must cross PCIe 3.0 x16 (about 12-13 GB/s theoretical per direction after encoding overhead): 8 bytes in and 4 bytes out. That is slower than the CPU's own DRAM bandwidth, so end-to-end GPU AXPY should lose to the CPU at every size. Pinned host memory should raise copy bandwidth but not change the conclusion.
