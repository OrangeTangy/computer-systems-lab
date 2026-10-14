"""Bound timed-region PMCs from CPU0 context-switch snapshots and identify the counter order.

python common/analyze-pmc.py SESSION
Reads sessions/SESSION/counters/{pmc.csv,pmc-export.log,index.jsonl,<tag>.json}. pmc.csv comes from
common/export-pmc.c run on the local ETL (whose SHA-256 is in etl-sha256.txt).

Windows did not report the PMC recording order (query error 24), so the order is derived from
physical invariants and every invariant is asserted. Missing counters are never turned into zeros.
"""

import collections, csv, json, pathlib, re, statistics, sys
from charts import plot

R = pathlib.Path(__file__).resolve().parents[1]
S = R / "sessions" / sys.argv[1]
C = S / "counters"
F = S / "figures"
log = (C / "pmc-export.log").read_text()
assert "events_lost=0 buffers_lost=0" in log and "ProcessTrace=0" in log, log
frequency = int(re.search(r"frequency=(\d+)", log)[1])
with (C / "pmc.csv").open(encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    next(reader)
    events = [[int(x) for x in row] for row in reader]
width = max(len(e) for e in events) - 3
assert width == 5, width
index = [json.loads(x) for x in (C / "index.jsonl").read_text(encoding="utf-8-sig").splitlines()]


def bounds(bench):
    """Lower = complete scheduling intervals inside the QPC window; upper = all intersecting intervals."""
    tid, start, end = bench["thread_id"], bench["qpc_start"], bench["qpc_end"]
    lo = [0] * width
    hi = [0] * width
    inside = 0
    n_in = n_edge = bad = 0
    for prev, cur in zip(events, events[1:]):
        if cur[2] != tid or cur[0] <= start or prev[0] >= end:
            continue
        if cur[0] < prev[0] or prev[1] != tid or len(prev) != 3 + width or len(cur) != 3 + width:
            bad += 1
            continue
        d = [b - a for a, b in zip(prev[3:], cur[3:])]
        if any(v < 0 for v in d):
            bad += 1
            continue
        hi = [a + b for a, b in zip(hi, d)]
        if prev[0] >= start and cur[0] <= end:
            lo = [a + b for a, b in zip(lo, d)]
            inside += cur[0] - prev[0]
            n_in += 1
        else:
            n_edge += 1
    assert not bad, (bench, "missing/reordered/reset counter intervals", bad)
    assert n_in > 0 and sum(hi) > 0, (bench, "no attributable interior PMC intervals")
    return lo, hi, inside / frequency, n_in, n_edge


runs = []
for e in index:
    b = json.loads((C / (e["tag"] + ".json")).read_text(encoding="utf-8-sig"))
    assert b["correct"] and b["qpc_frequency"] == frequency
    lo, hi, seconds, n_in, n_edge = bounds(b)
    ops = b["operations"] if "operations" in b else b["n"] * b["reps"]
    window = (b["qpc_end"] - b["qpc_start"]) / frequency
    runs.append(
        dict(
            tag=e["tag"],
            group=e["tag"].rsplit("-", 1)[0],
            bench=b,
            ops=ops,
            lo=lo,
            hi=hi,
            scheduled_s=seconds,
            window_s=window,
            interior=n_in,
            edge=n_edge,
        )
    )
by = {}
for r in runs:
    by.setdefault(r["group"], []).append(r)


def per_op(group, col):
    return statistics.median(r["lo"][col] / r["ops"] for r in by[group])


def rate(r, col):
    return r["lo"][col] / r["scheduled_s"] / 1e9


# ---- Identify recording order from invariants (each assertion is recorded as evidence) ----
evidence = []
cyc = [
    c
    for c in range(width)
    if all(2.0 < rate(r, c) < 5.5 for r in runs)
    and statistics.pstdev([rate(r, c) for r in runs]) / statistics.mean([rate(r, c) for r in runs])
    < 0.06
]
assert len(cyc) == 1, cyc
cyc = cyc[0]
evidence.append(
    f"TotalCycles = column {cyc}: the only counter whose rate stays between 2 and 5.5 G/s with <6% spread across all {len(runs)} workloads (memory chains and SIMD alike); a clock is workload-independent."
)
rest = [c for c in range(width) if c != cyc]
ins = max(rest, key=lambda c: per_op("L1-candidate", c))
for g in ["simd-float-scalar", "simd-float-native", "simd-double-auto"]:
    a, b = per_op(g + "-1024", ins), per_op(g + "-16777216", ins)
    assert abs(a / b - 1) < 0.1, (g, a, b)
evidence.append(
    f"InstructionRetired = column {ins}: largest non-clock count per L1-resident load, and per-element counts for each SIMD build are size-independent (within 10% between N=1,024 and N=16,777,216) because the same loop body executes."
)
rest.remove(ins)
l1t = [c for c in rest if per_op("LLC-candidate", c) > 0.3]
assert len(l1t) == 1, l1t
l1t = l1t[0]
rest.remove(l1t)
evidence.append(
    f"LabL1DTLBMiss = column {l1t}: the 4 MiB chain touches 1,024 pages, more than the 64-entry L1 DTLB but fewer than the 2,048-entry L2 DTLB and with data resident in the 16 MiB L3, so it is the only remaining counter that is high there."
)
# Both remaining counters are high for the 64 MiB chain (it misses the L2 DTLB and DRAM). The scattered chain
# separates them: 16,384 pages overflow the L2 DTLB, but its 16,384 lines are only 1 MiB of data, which stays cached.
l2t = [c for c in rest if per_op("scattered-pages", c) > 0.3 and per_op("LLC-candidate", c) < 0.01]
dram = [
    c
    for c in rest
    if per_op("DRAM-candidate", c) > 0.5
    and per_op("scattered-pages", c) < 0.2
    and per_op("L1-candidate", c) < 0.01
]
assert len(l2t) == 1 and len(dram) == 1 and l2t != dram, (l2t, dram)
l2t, dram = l2t[0], dram[0]
assert all(r["lo"][l1t] >= r["lo"][l2t] for r in runs if not r["group"].startswith("simd"))
evidence.append(
    f"LabL2DTLBMiss = column {l2t}: high for the scattered chain (16,384 pages, beyond the 8 MiB L2 DTLB reach) and near zero for the 4 MiB chain; it never exceeds column {l1t} in any memory run, as required because unit mask 0xF0 is a subset of 0xFF."
)
evidence.append(
    f"LabDemandDRAMFill = column {dram}: about one event per load for the 64 MiB chain, but low for the scattered chain, whose 1 MiB of touched lines fits in cache even though its pages do not fit the TLB, and near zero in L1."
)
order = {
    cyc: "TotalCycles",
    ins: "InstructionRetired",
    dram: "LabDemandDRAMFill",
    l1t: "LabL1DTLBMiss",
    l2t: "LabL2DTLBMiss",
}
names = [order[c] for c in range(width)]


def med(vals):
    return statistics.median(vals), min(vals), max(vals)


def iv(v, p=3):
    return f"{v[0]:.{p}f} [{v[1]:.{p}f}, {v[2]:.{p}f}]"


def metric(group, fn):
    return med([fn(r) for r in by[group]])


records = []
for r in runs:
    rec = {k: r[k] for k in ["tag", "group", "ops", "scheduled_s", "window_s", "interior", "edge"]}
    rec["benchmark"] = r["bench"]
    rec["counters"] = {
        names[c]: {
            "lower": r["lo"][c],
            "upper": r["hi"][c],
            "per_op_lower": r["lo"][c] / r["ops"],
            "per_op_upper": r["hi"][c] / r["ops"],
        }
        for c in range(width)
    }
    records.append(rec)
coverage = min(r["scheduled_s"] / r["window_s"] for r in runs)
(S / "counters.json").write_text(
    json.dumps(
        {
            "recording_order": names,
            "order_evidence": evidence,
            "qpc_frequency": frequency,
            "event_loss": 0,
            "min_scheduled_fraction_of_window": coverage,
            "scope": "CPU0 context-switch intervals of the exact benchmark thread inside its QPC timing window",
            "records": records,
        },
        indent=2,
    )
)

# ---- Memory hierarchy table ----
mem = [
    ("L1-candidate", "16 KiB", 16),
    ("L2-candidate", "256 KiB", 256),
    ("LLC-candidate", "4 MiB", 4096),
    ("DRAM-candidate", "64 MiB", 65536),
    ("packed-pages", "1 MiB, 64 B spacing", 1024),
    ("scattered-pages", "64 MiB, 4 KiB spacing", 65536),
]
cpl = lambda r: r["lo"][cyc] / r["ops"]
ghz = lambda r: rate(r, cyc)
mrows = []
M = {}
for g, label, _ in mem:
    M[g] = {
        k: metric(g, f)
        for k, f in [
            ("ns", lambda r: r["bench"]["ns_per_op"]),
            ("cyc", cpl),
            ("ghz", ghz),
            ("ins", lambda r: r["lo"][ins] / r["ops"]),
            ("l1t", lambda r: r["lo"][l1t] / r["ops"]),
            ("l2t", lambda r: r["lo"][l2t] / r["ops"]),
            ("dram", lambda r: r["lo"][dram] / r["ops"]),
        ]
    }
    m = M[g]
    mrows.append(
        f'| {label} | {iv(m["ns"],2)} | {iv(m["cyc"],1)} | {m["ghz"][0]:.2f} | {m["l1t"][0]:.4f} | {m["l2t"][0]:.4f} | {m["dram"][0]:.4f} |'
    )
# Two-level AMAT fit from the LLC and DRAM candidates: cycles = t_hit + m_DRAM * penalty
(tL, mL), (tD, mD) = [
    (M[g]["cyc"][0], M[g]["dram"][0]) for g in ["LLC-candidate", "DRAM-candidate"]
]
penalty = (tD - tL) / (mD - mL)
hit = tL - mL * penalty
pk, sc = M["packed-pages"], M["scattered-pages"]
pred_sc = hit + sc["dram"][0] * penalty
walk_upper = (sc["cyc"][0] - pk["cyc"][0]) / (sc["l2t"][0] - pk["l2t"][0])
walk_adj = (sc["cyc"][0] - pk["cyc"][0] - (sc["dram"][0] - pk["dram"][0]) * penalty) / (
    sc["l2t"][0] - pk["l2t"][0]
)
cap_model = 1 - 16 / 64

# ---- SIMD table ----
srows = []
SIMD = {}
for dt in ["float", "double"]:
    for b in ["scalar", "auto", "native"]:
        for n in [1024, 16777216]:
            g = f"simd-{dt}-{b}-{n}"
            s = {
                k: metric(g, f)
                for k, f in [
                    ("cpe", cpl),
                    ("ipe", lambda r: r["lo"][ins] / r["ops"]),
                    ("ipc", lambda r: r["lo"][ins] / r["lo"][cyc]),
                    ("tsc", lambda r: r["bench"]["tsc_ticks_element"]),
                    ("ghz", ghz),
                    ("dram", lambda r: r["lo"][dram] / r["ops"]),
                    ("gf", lambda r: r["bench"]["gflops"]),
                ]
            }
            SIMD[g] = s
            srows.append(
                f'| {dt} | {b} | {n:,} | {iv(s["cpe"])} | {s["ipe"][0]:.3f} | {s["ipc"][0]:.2f} | {s["tsc"][0]:.3f} | {s["ghz"][0]:.2f} | {s["dram"][0]:.4f} | {s["gf"][0]:.2f} |'
            )
clock = statistics.median(ghz(r) for r in runs)
fs, fn = SIMD["simd-float-scalar-1024"], SIMD["simd-float-native-1024"]
fsL, fnL = SIMD["simd-float-scalar-16777216"], SIMD["simd-float-native-16777216"]
bytes_per_cycle = 12 / fnL["cpe"][0]

# ---- Figures ----
plot(
    F / "counters-memory.svg",
    "Zen 3 counters per dependent load",
    "Footprint (KiB, log2)",
    "Events per load",
    [
        (n, [(kib, *M[g][k]) for g, _, kib in mem[:4]])
        for n, k in [
            ("L1 DTLB misses", "l1t"),
            ("L2 DTLB misses", "l2t"),
            ("Demand DRAM fills", "dram"),
        ]
    ],
    True,
    "Random 64 B chains, CPU0, 3 runs (whiskers min-max). Lines: L1D 32K, L2 512K, L2 DTLB reach 8M, L3 16M.",
    [(32, "L1D"), (512, "L2"), (8192, "DTLB"), (16384, "L3")],
)
plot(
    F / "counters-simd.svg",
    "Core cycles per element (measured, AXPY float32)",
    "Elements N (log2)",
    "Core cycles / element",
    [
        (b, [(n, *SIMD[f"simd-float-{b}-{n}"]["cpe"]) for n in [1024, 16777216]])
        for b in ["scalar", "auto", "native"]
    ],
    True,
    "TotalCycles PMC in the timed loop; vector builds lose their advantage once the arrays stream from DRAM.",
)

L = [
    "# Hardware-counter results (AMD Zen 3, Ryzen 5 5500)",
    "",
    "This closes the cache/TLB-correlation and core-cycles-per-element gaps that earlier revisions left open. Every value below is a measured count from the AMD core PMU, captured with Windows Performance Recorder during the same benchmark runs whose timings are listed. Nothing is inferred from timing alone.",
    "",
    "## How the counts were obtained",
    "",
    f"- **Capture:** `wpr` with the strict profile [`counters-zen3.wprp`](counters/counters-zen3.wprp) recorded five PMCs on every context switch (CSwitch) while each benchmark ran pinned to CPU0. {len(runs)} runs: six memory conditions and twelve SIMD conditions, three repetitions each, three seconds per run.",
    "- **Export:** [`common/export-pmc.c`](../../common/export-pmc.c) reads the ETL through the Windows ETW API and keeps CPU0 context switches. Export reported zero lost events and zero lost buffers. The 500 MB ETL stays local because it contains unrelated system activity; its SHA-256 is in [`counters/etl-sha256.txt`](counters/etl-sha256.txt).",
    f"- **Attribution:** for each run, only scheduling intervals in which the benchmark's own thread ran on CPU0 are summed. The **lower** bound uses intervals completely inside the QPC timing window; the **upper** bound adds the two edge intervals. Tables use the lower bound; both are in [`counters.json`](counters.json). The thread was scheduled for at least {100*coverage:.1f}% of every timing window.",
    "- **Normalization:** memory counts are per dependent load (`operations`); SIMD counts are per processed element (`n x reps`). Loop, timer and stop-check overhead are included, initialization and validation are not.",
    "",
    "### Identifying the counter order",
    "",
    "Windows did not report the order in which it recorded the five counters (`counter-order.txt`: query error 24), which is why the previous revision stopped here. Rather than guess, [`analyze-pmc.py`](../../common/analyze-pmc.py) derives the order from physical invariants and fails if any invariant does not hold:",
    "",
    *[f"{i+1}. {t}" for i, t in enumerate(evidence)],
    "",
    f'Recovered order: `{", ".join(names)}`.',
    "",
    "## Project 2: cache and TLB correlation",
    "",
    "![Counters per load](figures/counters-memory.svg)",
    "",
    "| Condition | ns/load [min,max] | Core cycles/load [min,max] | Core GHz | L1 DTLB miss/load | L2 DTLB miss/load | DRAM fill/load |",
    "|---|---|---|---:|---:|---:|---:|",
    *mrows,
    "",
    "**What the counters show:**",
    "",
    f'- **L1 is about {M["L1-candidate"]["cyc"][0]:.1f} cycles per load.** Zen 3\'s documented L1D load-to-use latency is 4 cycles for simple addressing, so the 16 KiB chain is an L1 measurement, and the timer agrees with the cycle counter ({M["L1-candidate"]["ns"][0]:.2f} ns x {M["L1-candidate"]["ghz"][0]:.2f} GHz = {M["L1-candidate"]["ns"][0]*M["L1-candidate"]["ghz"][0]:.2f} cycles). This independently validates the timing method.',
    f'- **L2 is about {M["L2-candidate"]["cyc"][0]:.1f} cycles** (documented: 12) with essentially no TLB misses: 256 KiB is 64 pages, exactly the L1 DTLB reach.',
    f'- **The 4 MiB "LLC" point costs {M["LLC-candidate"]["cyc"][0]:.1f} cycles but is not a pure L3 latency:** {M["LLC-candidate"]["l1t"][0]:.2f} L1 DTLB misses per load (1,024 pages against a 64-entry L1 DTLB) add L2-TLB lookups to most loads. L2 DTLB misses stay near zero because 1,024 pages fit its 2,048 entries, and DRAM fills are only {M["LLC-candidate"]["dram"][0]:.3f}/load, so data really comes from L3.',
    f'- **The 64 MiB chain is DRAM-bound:** {M["DRAM-candidate"]["dram"][0]:.2f} demand DRAM fills and {M["DRAM-candidate"]["l2t"][0]:.2f} L2 DTLB misses (page walks) per load, costing about {M["DRAM-candidate"]["cyc"][0]:.0f} cycles per load.',
    "",
    "### AMAT-style decomposition",
    "",
    f'Using the counted DRAM-fill rate as the miss probability, a two-level model `cycles/load = t_hit + m_DRAM x penalty` fitted to the LLC and DRAM candidates gives **t_hit = {hit:.1f} cycles** and **penalty = {penalty:.0f} cycles ({penalty/clock:.0f} ns at {clock:.2f} GHz)**. The penalty absorbs the page walks that co-occur with DRAM misses in the 64 MiB chain, so it is a "DRAM plus translation" penalty rather than pure DRAM access time.',
    "",
    f'**Anomaly retained:** a capacity-only model predicts that about {100*(1-cap_model):.0f}% of a 64 MiB random footprint stays in the 16 MiB L3 (miss rate {cap_model:.2f}), but the counters show {M["DRAM-candidate"]["dram"][0]:.2f} demand DRAM fills per load. Plausible contributors: Zen 3\'s L3 is a non-inclusive victim cache filled by L2 evictions rather than demand fills, page-table lines compete for the same capacity, and other processes share the L3. The event also counts I/O fills, and may count page-walk fills; the counter definition alone cannot separate these.',
    "",
    "### TLB impact: same nodes, different pages",
    "",
    f'`packed-pages` and `scattered-pages` both chase **16,384 nodes** in random order; only the spacing changes (64 B, i.e. 256 pages, versus 4 KiB, i.e. 16,384 pages). The counters confirm the intended effect: L2 DTLB misses rise from {pk["l2t"][0]:.4f} to {sc["l2t"][0]:.2f} per load, and L1 DTLB misses from {pk["l1t"][0]:.2f} to {sc["l1t"][0]:.2f}. Time per load rises from {pk["cyc"][0]:.1f} to {sc["cyc"][0]:.1f} cycles.',
    "",
    f'Dividing the extra cycles by the extra L2 DTLB misses gives an upper bound of **{walk_upper:.0f} cycles per page walk**. Removing the small DRAM-fill increase ({pk["dram"][0]:.3f} to {sc["dram"][0]:.3f}/load, at the fitted {penalty:.0f}-cycle penalty) gives about **{walk_adj:.0f} cycles per walk**, consistent with walks whose page-table entries hit in the L2/L3 caches. **Remaining confound:** 4 KiB spacing also maps every node to the same L1/L2 set index, so set-conflict misses could contribute; there was no L2-miss counter in this five-counter profile to exclude them. The AMAT model with no TLB term predicts {pred_sc:.0f} cycles for the scattered chain; the measured {sc["cyc"][0]:.0f} leaves the remainder for translation and set conflicts.',
    "",
    "## Project 1: measured core cycles per element",
    "",
    "![SIMD cycles](figures/counters-simd.svg)",
    "",
    "All twelve conditions use kernel 0 (out-of-place AXPY, `z = 1.25x + y`, FMA contraction off). TSC ticks run at a fixed reference rate and are not core cycles; both are shown so the difference is visible.",
    "",
    "| Type | Build | N | Core cycles/element [min,max] | Instr/element | IPC | TSC ticks/element | Core GHz | DRAM fill/element | GFLOP/s |",
    "|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
    *srows,
    "",
    "**What the counters show:**",
    "",
    f'- **Vectorization is confirmed by instruction counts.** Float32 scalar AXPY retires {fs["ipe"][0]:.2f} instructions per element; the AVX2 build retires {fn["ipe"][0]:.2f}, an {fs["ipe"][0]/fn["ipe"][0]:.1f}x reduction that matches 8 float lanes per 256-bit instruction plus loop overhead amortized over the unrolled body.',
    f'- **In cache, the speedup is a cycle-count speedup:** {fs["cpe"][0]:.3f} versus {fn["cpe"][0]:.3f} cycles/element ({fs["cpe"][0]/fn["cpe"][0]:.2f}x) at nearly the same clock.',
    f'- **The scalar baseline is dispatch-bound, not arithmetic-bound.** In L1 the scalar builds run at {fs["ipc"][0]:.1f}-{SIMD["simd-double-scalar-1024"]["ipc"][0]:.1f} IPC, close to Zen 3\'s 6-wide dispatch (the compare-and-branch pair fuses, so 7 instructions are about 6 macro-ops). One element per ~1.2 cycles is the front-end limit, so SIMD wins in cache mainly by issuing fewer instructions, not by doing arithmetic faster.',
    f'- **From DRAM, the vector advantage disappears** ({fsL["cpe"][0]:.2f} versus {fnL["cpe"][0]:.2f} cycles/element) even though the vector build still executes {fsL["ipe"][0]/fnL["ipe"][0]:.1f}x fewer instructions. IPC of the native build drops from {fn["ipc"][0]:.2f} to {fnL["ipc"][0]:.2f}: the core is idle, waiting for data. This is the memory-bound regime of the roofline, measured directly rather than inferred.',
    f'- **Bandwidth consistency check:** 12 useful bytes per element at {fnL["cpe"][0]:.2f} cycles/element is {bytes_per_cycle:.2f} B/cycle, i.e. {bytes_per_cycle*fnL["ghz"][0]:.1f} GB/s at {fnL["ghz"][0]:.2f} GHz, in line with the separately measured two-read/one-write streaming reference (about 16-18 GB/s).',
    f'- **Negative case explained by counters:** for float64 from DRAM the AVX2 build is *slower* than scalar ({SIMD["simd-double-native-16777216"]["cpe"][0]:.2f} versus {SIMD["simd-double-scalar-16777216"]["cpe"][0]:.2f} cycles/element) and incurs {SIMD["simd-double-native-16777216"]["dram"][0]/SIMD["simd-double-scalar-16777216"]["dram"][0]:.0f}x more demand DRAM fills per element ({SIMD["simd-double-native-16777216"]["dram"][0]:.3f} versus {SIMD["simd-double-scalar-16777216"]["dram"][0]:.4f}). The wider loop consumes cache lines faster than the hardware prefetcher stays ahead, so more loads wait for demand fills. Wider vectors cannot help, and can hurt, once the stream is limited by prefetch and DRAM.',
    f'- **Clock:** the core ran at a median {clock:.2f} GHz under load, essentially the 5500\'s rated 4.2 GHz maximum boost, so the roofline compute ceiling can now use a measured clock instead of 2/3/4 GHz scenarios: two 256-bit FMA pipes give 32 FP32 FLOP/cycle, **{32*clock:.0f} GFLOP/s** with FMA; this build disables FMA contraction. For AXPY in L1 the tighter limit is memory ports: each 8-element vector needs two 256-bit loads and one 256-bit store, so at one 256-bit store per cycle the floor is about 0.125 cycles/element. The measured {fn["cpe"][0]:.3f} is {0.125/fn["cpe"][0]*100:.0f}% of that port bound.',
    "",
    "Demand DRAM fills per element stay small even for DRAM-resident arrays because sequential streams are brought in by the hardware prefetcher, and prefetch fills are not demand fills. That is why this event says little about streaming kernels and why the memory-chain conditions are the right place to use it.",
    "",
    "## Limits",
    "",
    "- Five events at a time (six programmable sources were listed; one was left free). No L2-miss or L3-miss counter was recorded, so L2 versus L3 hit rates are inferred from footprint rather than counted.",
    "- Counts are attributed per context-switch interval, not per instruction. Edge intervals are bounded, not split.",
    "- Three runs per condition. Medians and min/max are reported; these are not confidence intervals.",
    "- Counter definitions follow the Linux perf Zen 3 event table (see [Zen 3 counter notes](../../project-2-memory/docs/ZEN3-COUNTERS.md)); speculative counts are possible for TLB events.",
]
(S / "COUNTERS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("order:", names)
print(
    f"Validated {len(runs)} counter runs; AMAT hit={hit:.1f} penalty={penalty:.0f}; walk upper={walk_upper:.0f} adj={walk_adj:.0f}; clock={clock:.2f}"
)
