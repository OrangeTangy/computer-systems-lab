"""Optional GPU extension: CPU-vs-GPU out-of-place AXPY (z = 1.25x + y, float32).

python project-1-simd/scripts/gpu_axpy.py collect SESSION   (needs CuPy and an NVIDIA GPU)
python project-1-simd/scripts/gpu_axpy.py analyze SESSION   (standard library only; reuses the session's CPU simd.jsonl)
Kernel-only time (CUDA events around back-to-back launches) is kept separate from end-to-end time
(host-to-device copy + kernel + device-to-host copy), for pageable and pinned host buffers.
"""

import json, pathlib, random, statistics, sys, time, datetime

R = pathlib.Path(__file__).resolve().parents[2]
mode, session = sys.argv[1], sys.argv[2]
S = R / "sessions" / session
out = S / "gpu"
SIZES = [1024, 8192, 65536, 524288, 4194304, 16777216, 67108864]
TRIALS = 5


def collect():
    import cupy as cp, numpy as np

    out.mkdir(exist_ok=False)
    (out / "HYPOTHESES.md").write_text(
        """# Predictions before the GPU extension (written before collection)

- **Kernel-only:** AXPY moves 12 bytes per 2 FLOPs, so the GPU kernel should be memory-bound and approach a large fraction of the 1660 Ti's 288 GB/s at large N, roughly 10x the CPU's ~18 GB/s DRAM stream. At small N a fixed launch overhead of several microseconds should make the GPU slower than the in-cache CPU.
- **End-to-end:** every element must cross PCIe 3.0 x16 (about 12-13 GB/s theoretical per direction after encoding overhead): 8 bytes in and 4 bytes out. That is slower than the CPU's own DRAM bandwidth, so end-to-end GPU AXPY should lose to the CPU at every size. Pinned host memory should raise copy bandwidth but not change the conclusion.
"""
    )
    props = cp.cuda.runtime.getDeviceProperties(0)
    env = {
        "start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "device": props["name"].decode(),
        "sm_count": props["multiProcessorCount"],
        "sm_clock_khz": props["clockRate"],
        "memory_clock_khz": props["memoryClockRate"],
        "memory_bus_bits": props["memoryBusWidth"],
        "theoretical_GB_s": 2 * props["memoryClockRate"] * 1e3 * props["memoryBusWidth"] / 8 / 1e9,
        "cupy": cp.__version__,
        "numpy": np.__version__,
        "cuda_runtime": cp.cuda.runtime.runtimeGetVersion(),
        "cuda_driver": cp.cuda.runtime.driverGetVersion(),
        "trials": TRIALS,
    }
    k = cp.ElementwiseKernel("float32 x, float32 y", "float32 z", "z = 1.25f * x + y", "lab_axpy")
    ev = lambda: cp.cuda.Event()

    def span(a, b):
        b.synchronize()
        return cp.cuda.get_elapsed_time(a, b) / 1e3

    order = [(n, t) for n in SIZES for t in range(TRIALS)]
    random.Random(4320).shuffle(order)
    rows = []
    for seq, (n, trial) in enumerate(order):
        i = np.arange(n)
        x = (((i % 31) - 15) / 32).astype(np.float32)
        y = (((i % 17) - 8) / 16).astype(np.float32)
        ref = np.float32(1.25) * x + y
        dx, dy, dz = cp.asarray(x), cp.asarray(y), cp.empty(n, cp.float32)
        k(dx, dy, dz)
        cp.cuda.Device().synchronize()
        # Kernel-only: enough back-to-back launches to fill about 50 ms.
        a, b = ev(), ev()
        a.record()
        k(dx, dy, dz)
        b.record()
        one = span(a, b)
        reps = max(10, min(20000, int(0.05 / max(one, 1e-6))))
        a.record()
        for _ in range(reps):
            k(dx, dy, dz)
        b.record()
        kernel_s = span(a, b) / reps
        assert np.array_equal(cp.asnumpy(dz), ref)
        row = {"n": n, "trial": trial, "sequence": seq, "kernel_s": kernel_s, "kernel_reps": reps}
        for host in ["pageable", "pinned"]:
            if host == "pinned":
                import cupyx

                hx, hy, hz = (
                    cupyx.empty_pinned(n, np.float32),
                    cupyx.empty_pinned(n, np.float32),
                    cupyx.empty_pinned(n, np.float32),
                )
                hx[:] = x
                hy[:] = y
            else:
                hx, hy, hz = x, y, np.empty(n, np.float32)
            best = None
            for _ in range(
                3
            ):  # three end-to-end passes per trial; keep each pass's phases together
                e = [ev() for _ in range(4)]
                t0 = time.perf_counter()
                e[0].record()
                dx.set(hx)
                dy.set(hy)
                e[1].record()
                k(dx, dy, dz)
                e[2].record()
                dz.get(out=hz)
                e[3].record()
                e[3].synchronize()
                wall = time.perf_counter() - t0
                p = dict(
                    h2d_s=cp.cuda.get_elapsed_time(e[0], e[1]) / 1e3,
                    kern_s=cp.cuda.get_elapsed_time(e[1], e[2]) / 1e3,
                    d2h_s=cp.cuda.get_elapsed_time(e[2], e[3]) / 1e3,
                    wall_s=wall,
                )
                assert np.array_equal(hz, ref)
                best = p if best is None or p["wall_s"] < best["wall_s"] else best
            row[host] = best
        rows.append(row)
        print(f"GPU {seq+1}/{len(order)} n={n}", flush=True)
        del dx, dy, dz
        cp.get_default_memory_pool().free_all_blocks()
        cp.get_default_pinned_memory_pool().free_all_blocks()
    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    env["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / "environment.json").write_text(json.dumps(env, indent=2))


def analyze():
    sys.path.insert(0, str(R / "common"))
    from charts import plot

    rows = [json.loads(l) for l in (out / "results.jsonl").read_text().splitlines()]
    env = json.loads((out / "environment.json").read_text())
    cpu = [json.loads(l) for l in (S / "simd.jsonl").read_text().splitlines()]
    med = lambda v: (statistics.median(v), min(v), max(v))

    def g(n, f):
        return med([f(r) for r in rows if r["n"] == n])

    def c(n, b):
        v = [
            r["ns_element"]
            for r in cpu
            if r["dtype"] == "float"
            and r["build"] == b
            and r["kind"] == 0
            and r["stride"] == 1
            and r["offset_elements"] == 0
            and r["n"] == n
        ]
        return med(v) if v else None

    ns = lambda s, n: s * 1e9 / n
    tab = []
    series = {
        k: []
        for k in [
            "CPU scalar",
            "CPU AVX2 (native)",
            "GPU kernel only",
            "GPU end-to-end, pageable",
            "GPU end-to-end, pinned",
        ]
    }
    for n in SIZES:
        K = g(n, lambda r: ns(r["kernel_s"], n))
        P = g(n, lambda r: ns(r["pageable"]["wall_s"], n))
        Q = g(n, lambda r: ns(r["pinned"]["wall_s"], n))
        cs, cn = c(n, "scalar"), c(n, "native")
        series["GPU kernel only"].append((n, *K))
        series["GPU end-to-end, pageable"].append((n, *P))
        series["GPU end-to-end, pinned"].append((n, *Q))
        if cs:
            series["CPU scalar"].append((n, *cs))
            series["CPU AVX2 (native)"].append((n, *cn))
        h2d = g(n, lambda r: 8 * n / r["pinned"]["h2d_s"] / 1e9)[0]
        d2h = g(n, lambda r: 4 * n / r["pinned"]["d2h_s"] / 1e9)[0]
        gbs = 12 * n / statistics.median(r["kernel_s"] for r in rows if r["n"] == n) / 1e9
        tab.append(
            f"| {n:,} | "
            + (f"{cn[0]:.3f}" if cn else "not run")
            + f" |{K[0]:.4f} [{K[1]:.4f}, {K[2]:.4f}] | {gbs:.1f} | {P[0]:.3f} | {Q[0]:.3f} | {h2d:.1f} / {d2h:.1f} | "
            + (f"{cn[0]/K[0]:.2f}x / {cn[0]/Q[0]:.2f}x" if cn else "n/a (no CPU run)")
            + " |"
        )
    F = S / "figures"
    plot(
        F / "gpu-axpy.svg",
        "CPU vs GPU AXPY time per element (float32)",
        "Elements N (log2)",
        "ns per element (lower is better)",
        [(k, v) for k, v in series.items() if v],
        True,
        "Same machine. GPU kernel-only uses CUDA events; end-to-end adds H2D (x,y) and D2H (z) copies. Medians of 5 trials, whiskers min-max.",
    )
    big = SIZES[-2]
    Kb = g(big, lambda r: r["kernel_s"])[0]
    Pb = g(big, lambda r: r["pinned"]["wall_s"])[0]
    share = g(
        big,
        lambda r: (r["pinned"]["h2d_s"] + r["pinned"]["d2h_s"])
        / (r["pinned"]["h2d_s"] + r["pinned"]["kern_s"] + r["pinned"]["d2h_s"]),
    )[0]
    small = g(SIZES[0], lambda r: r["kernel_s"])[0]
    L = [
        "# Optional GPU extension: CPU vs GPU AXPY",
        "",
        f'Device: **{env["device"]}** ({env["sm_count"]} SMs, {env["memory_bus_bits"]}-bit memory, {env["theoretical_GB_s"]:.0f} GB/s theoretical), CUDA runtime {env["cuda_runtime"]}, driver {env["cuda_driver"]}, CuPy {env["cupy"]}. Same host as the CPU results (Ryzen 5 5500, PCIe 3.0). [Predictions](gpu/HYPOTHESES.md) were written before collection; [raw results](gpu/results.jsonl).',
        "",
        "The GPU computes exactly the CPU kernel, out-of-place `z = 1.25x + y` in float32, and every result is checked bit-for-bit against a NumPy reference (inputs are binary fractions, so the result is exact). **Kernel-only** time is measured with CUDA events around back-to-back launches. **End-to-end** time is wall-clock for copying x and y to the device, running the kernel, and copying z back, into preallocated device buffers; it is reported for ordinary (pageable) and page-locked (pinned) host memory. CPU numbers are the native AVX2 build from this session's SIMD suite.",
        "",
        "![CPU vs GPU](figures/gpu-axpy.svg)",
        "",
        "| N | CPU AVX2 ns/elem | GPU kernel ns/elem [min,max] | GPU kernel GB/s | E2E pageable ns/elem | E2E pinned ns/elem | Pinned H2D / D2H GB/s | CPU-to-GPU speedup: kernel / E2E pinned |",
        "|---:|---:|---|---:|---:|---:|---:|---:|",
        *tab,
        "",
        "**When the GPU helps:** with data already resident on the device, a large AXPY runs at "
        + f'{12*big/Kb/1e9:.0f} GB/s ({100*12*big/Kb/1e9/env["theoretical_GB_s"]:.0f}% of theoretical), '
        + f'{c(big,"native")[0]*1e-9*big/Kb:.0f}x faster per element than the CPU\'s DRAM-limited AVX2 loop at the same N. That is the situation of a longer GPU pipeline where data stays on the card between kernels.',
        "",
        f"**When it fails:** (1) at small N, a single launch costs about {small*1e6:.1f} us regardless of work, so the in-cache CPU is far faster; (2) end-to-end, AXPY does only 2 FLOPs per 12 bytes, and the bytes must cross PCIe. At N={big:,} with pinned memory, copies are {100*share:.0f}% of the GPU-side time, and the end-to-end path is limited by PCIe bandwidth, which is lower than the CPU's own DRAM bandwidth. Offloading a single low-intensity kernel therefore loses, the same roofline argument as on the CPU with PCIe as the narrowest link.",
        "",
        "**Limits:** one kernel, one GPU; pageable-copy timing includes the driver staging copy; the GPU clock is not locked; CuPy adds Python launch overhead that a native CUDA program would reduce (kernel-only timing with back-to-back launches minimizes but does not remove it). This extension is optional and not used for any required rubric item.",
    ]
    (S / "GPU.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("GPU report written")


collect() if mode == "collect" else analyze()
