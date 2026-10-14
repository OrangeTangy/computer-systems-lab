"""Report for the SIMD extension (int32 type comparison, stencil, gather). Standard library only.

python project-1-simd/scripts/analyze_ext.py SESSION
"""

import collections, json, pathlib, statistics, sys

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "common"))
from charts import plot

S = R / "sessions" / sys.argv[1]
E = S / "simd-extension"
F = S / "figures"
rows = [json.loads(l) for l in (E / "results.jsonl").read_text().splitlines()] + (
    [json.loads(l) for l in (E / "results-forcegather.jsonl").read_text().splitlines()]
    if (E / "results-forcegather.jsonl").exists()
    else []
)
env = json.loads((E / "environment.json").read_text())
assert all(r["correct"] for r in rows)
c = collections.Counter(
    (r["dtype"], r["build"], r["kind"], r["random_index"], r["n"]) for r in rows
)
assert set(c.values()) == {env["trials"]}, c
G = collections.defaultdict(list)
for r in rows:
    G[r["dtype"], r["build"], r["kind"], r["random_index"], r["n"]].append(r["ns_element"])
m = lambda k: (statistics.median(G[k]), min(G[k]), max(G[k]))
iv = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
sizes = sorted({r["n"] for r in rows})
caches = [(32, "L1D 32K"), (512, "L2 512K"), (16384, "L3 16M")]
ev = {(b["dtype"], b["variant"]): b["kernels"] for b in env["builds"]}


def vec(t, v, fn):
    k = ev[t, v][fn]
    return f"{k['ymm']} ymm / {k['xmm']} xmm / {k['gather']} gather"


L = [
    "# SIMD extension: data types, stencil and gather",
    "",
    f'Same host and compiler as the main Ryzen session ({env["compiler"]}); new source [`simd_ext.c`](simd-extension/simd_ext.c), {len(rows)} validated runs, {env["trials"]} trials per condition, interleaved in a fixed shuffled order, pinned to CPU0, 0.2 s timing windows. [Predictions](simd-extension/HYPOTHESES.md) were written before collection. Every run is checked against a double-precision reference first (int32: exact). Builds: `scalar` = `-O3 -fno-tree-vectorize`, `auto` = `-O3` (SSE2 baseline), `native` = `-O3 -march=native` (AVX2), all with `-ffp-contract=off`. Compiler reports and per-kernel instruction counts are in [`simd-extension/evidence/`](simd-extension/evidence/).',
    "",
]
# ---- data types ----
L += [
    "## Data type: int32 vs float32 vs float64",
    "",
    "Kernel `z = 3x + y` with identical code for each type. Values are ns per element, median [min,max].",
    "",
    "| N | Footprint KiB (32-bit) | int32 scalar | int32 native | float32 scalar | float32 native | float64 scalar | float64 native | Native speedup i32 / f32 / f64 |",
    "|---:|---:|---|---|---|---|---|---|---|",
]
for n in sizes:
    v = {
        (t, b): m((t, b, 0, 0, n))
        for t in ["int32", "float", "double"]
        for b in ["scalar", "native"]
    }
    L.append(
        f"| {n:,} | {3*4*n//1024:,} | "
        + " | ".join(
            iv(v[t, b]) for t in ["int32", "float", "double"] for b in ["scalar", "native"]
        )
        + " | "
        + " / ".join(
            f'{v[t,"scalar"][0]/v[t,"native"][0]:.2f}x' for t in ["int32", "float", "double"]
        )
        + " |"
    )
plot(
    F / "ext-dtype.svg",
    "Native AVX2 time per element by data type (z = 3x + y)",
    "Elements N (log2)",
    "ns / element",
    [(t, [(n, *m((t, "native", 0, 0, n))) for n in sizes]) for t in ["int32", "float", "double"]],
    True,
    "Footprint = 3 arrays; 32-bit types use 12 B/element, float64 24 B/element.",
)
i32, f32, f64 = [m((t, "native", 0, 0, sizes[0]))[0] for t in ["int32", "float", "double"]]
I, Fl, D = [m((t, "native", 0, 0, sizes[-1]))[0] for t in ["int32", "float", "double"]]
L += [
    "",
    "![Data types](figures/ext-dtype.svg)",
    "",
    f"**Interpretation.** In L1 (N={sizes[0]:,}) int32 and float32 cost {i32:.3f} and {f32:.3f} ns/element: both pack 8 lanes per 256-bit register, so lane count, not integer versus floating point, sets the rate. Float64 has 4 lanes and costs {f64:.3f} ns ({f64/f32:.2f}x float32). From DRAM (N={sizes[-1]:,}) the ratio float64/float32 is {D/Fl:.2f}x, close to the 2x byte ratio, because both are moving data at the same bandwidth; int32/float32 is {I/Fl:.2f}x. Vector width per type matters in cache; bytes per element matter from memory.",
    "",
]
# ---- stencil ----
L += [
    "## 1D three-point stencil",
    "",
    "`z[i] = 0.25x[i-1] + 0.5x[i] + 0.25x[i+1]`: 5 FLOPs per output (3 multiplies, 2 adds) and 8 useful bytes (one read of x, one write of z for float32), so the useful arithmetic intensity is 5/8 = 0.625 FLOP/B for float32, compared with 1/6 for AXPY.",
    "",
    f'Vector evidence (stencil kernel, native build): {vec("float","native","stencil")} instructions; scalar build: {vec("float","scalar","stencil")}.',
    "",
    "| Type | N | Scalar ns/elem | Auto ns/elem | Native ns/elem | Native speedup | Native GFLOP/s |",
    "|---|---:|---|---|---|---:|---:|",
]
for t in ["float", "double"]:
    for n in sizes:
        s, a, nv = [m((t, b, 3, 0, n)) for b in ["scalar", "auto", "native"]]
        L.append(
            f"| {t} | {n:,} | {iv(s)} | {iv(a)} | {iv(nv)} | {s[0]/nv[0]:.2f}x | {5/nv[0]:.2f} |"
        )
plot(
    F / "ext-stencil.svg",
    "Float32 stencil: locality sweep",
    "Elements N (log2)",
    "ns / output element",
    [(b, [(n, *m(("float", b, 3, 0, n))) for n in sizes]) for b in ["scalar", "auto", "native"]],
    True,
    "2 arrays; footprint = 8 B x N for float32.",
)
sx = [
    m(("float", "scalar", 0, 0, n))[0] / m(("float", "native", 0, 0, n))[0]
    for n in [sizes[0], sizes[-1]]
]
st = [
    m(("float", "scalar", 3, 0, n))[0] / m(("float", "native", 3, 0, n))[0]
    for n in [sizes[0], sizes[-1]]
]
L += [
    "",
    "![Stencil](figures/ext-stencil.svg)",
    "",
    f"**Interpretation.** In cache the stencil gains {st[0]:.2f}x from AVX2 versus {sx[0]:.2f}x for `3x + y`; from DRAM {st[1]:.2f}x versus {sx[1]:.2f}x. The stencil reuses each loaded x value in three outputs (neighbors overlap in registers and L1), so it does more arithmetic per byte fetched from memory and keeps more SIMD benefit when the arrays no longer fit in cache. It still compresses as the working set grows, which is the roofline argument: higher intensity moves the kernel right on the roofline, toward but not into the compute-bound region.",
    "",
]
# ---- gather ----
GB = ["scalar", "auto", "native", "native-nogather"] + (
    ["native-forcegather"] if ("float", "native-forcegather") in ev else []
)
L += [
    "## Gather-indexed multiply (negative case)",
    "",
    "`z[i] = x[idx[i]] * y[i]` with `idx` either the identity permutation (perfect locality, but the compiler cannot know that) or a random permutation. Float32 only.",
    "",
    "| Build | Flags beyond -O3 | Gather kernel: ymm / xmm / hardware gather instructions |",
    "|---|---|---|",
    *[
        f'| {b} | {fl} | {vec("float",b,"gather")} |'
        for b, fl in [
            ("scalar", "-fno-tree-vectorize"),
            ("auto", "(SSE2 baseline)"),
            ("native", "-march=native"),
            ("native-nogather", "-march=native, gathers disabled by -mtune-ctrl"),
            ("native-forcegather", "-march=native, gathers enabled by -mtune-ctrl"),
        ]
        if b in GB
    ],
    "",
    "| Index | N | " + " | ".join(GB) + " | Best vector / scalar |",
    "|---|---:|" + "---|" * len(GB) + "---:|",
]
for ix, name in [(0, "identity"), (1, "random")]:
    for n in sizes:
        v = [m(("float", b, 4, ix, n)) for b in GB]
        L.append(
            f"| {name} | {n:,} | "
            + " | ".join(iv(x) for x in v)
            + f" | {v[0][0]/min(x[0] for x in v[1:]):.2f}x |"
        )
plot(
    F / "ext-gather.svg",
    "Gather multiply: identity vs random index",
    "Elements N (log2)",
    "ns / element",
    [
        (f"{b}, {nm}", [(n, *m(("float", b, 4, ix, n))) for n in sizes])
        for ix, nm in [(0, "identity"), (1, "random")]
        for b in (
            ["scalar", "native", "native-forcegather"]
            if "native-forcegather" in GB
            else ["scalar", "native"]
        )
    ],
    True,
    "native = emulated gather (scalar loads into xmm); forcegather = AVX2 vgatherdps.",
)
s0 = m(("float", "scalar", 4, 0, sizes[0]))[0]
n0 = m(("float", "native", 4, 0, sizes[0]))[0]
fg = m(("float", "native-forcegather", 4, 0, sizes[0]))[0] if "native-forcegather" in GB else None
c0 = m(("float", "scalar", 0, 0, sizes[0]))[0] / m(("float", "native", 0, 0, sizes[0]))[0]
rs = [m(("float", b, 4, 1, sizes[-1]))[0] for b in GB]
ri = m(("float", "scalar", 4, 1, sizes[-1]))[0] / m(("float", "scalar", 4, 0, sizes[-1]))[0]
L += [
    "",
    "![Gather](figures/ext-gather.svg)",
    "",
    "**What the compiler actually did.** The plain AVX2 build contains **no hardware gather instruction**: GCC 16's Zen 3 tuning avoids `vgatherdps` and emits an *emulated gather*, scalar loads packed into 128-bit `xmm` registers followed by a vector multiply. The SSE2 `auto` build does the same, which is why `auto`, `native` and `native-nogather` perform identically. Only `native-forcegather` uses real 256-bit `vgatherdps`. A first compile check during this work wrongly reported gathers in the native build because it counted jump-target labels such as `<gather+0x40>` as instructions. The pre-collection prediction repeats that mistake and is left unedited. Checking mnemonics in the disassembly caught it: a flag or a quick text search is not proof of the instructions that run.",
    "",
    f"**Interpretation.** Even with a perfectly local identity index in L1, the emulated gather gains only {s0/n0:.2f}x over scalar, against {c0:.2f}x for the contiguous `3x + y` kernel at the same size: each lane is still a separate load, so vectorizing saves arithmetic instructions but not memory accesses."
    + (
        f' The hardware gather is {"slower" if fg>n0 else "faster"} than the emulated one ({fg:.3f} versus {n0:.3f} ns/element){f", and even slower than plain scalar code ({s0:.3f})" if fg>s0 else ""}, {"confirming that GCC\'s tuning choice is right for Zen 3, where vgatherdps is split into many micro-ops" if fg>n0 else "so the tuning default leaves performance unused on this core"}.'
        if fg
        else ""
    )
    + f" With a random index and N={sizes[-1]:,} every build takes {min(rs):.1f}-{max(rs):.1f} ns/element, {ri:.1f}x the identity-index time: each element is a random cache-line, and often page, access into a {4*sizes[-1]//2**20} MiB array. The core waits on memory latency and memory-level parallelism, so no form of SIMD helps. In L1 (N={sizes[0]:,}) random and identity indices cost the same; access order starts to matter once x leaves the L1/L2 caches.",
    "",
    "## Limits",
    "",
    "- 0.2 s windows and five trials; min/max ranges are not confidence intervals.",
    "- Footprints are logical bytes; physical traffic (write-allocate, prefetch) was not counted in this extension.",
    "- Gather results depend on the microarchitecture: Zen 3 implements AVX2 gathers as multiple micro-ops; other cores (for example recent Intel) have faster gathers.",
]
(S / "SIMD-EXTENSION.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("SIMD extension report written")
