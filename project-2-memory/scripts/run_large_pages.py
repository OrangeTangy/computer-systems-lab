"""4 KiB versus 2 MiB pages for dependent random chains (needs SeLockMemoryPrivilege).

python project-2-memory/scripts/run_large_pages.py collect SESSION [--gcc gcc]
python project-2-memory/scripts/run_large_pages.py analyze SESSION
Writes sessions/SESSION/large-pages/ (collect refuses an existing directory) and sessions/SESSION/LARGE-PAGES.md.
"""

import argparse, collections, datetime, hashlib, json, pathlib, random, shutil, statistics, subprocess, sys

p = argparse.ArgumentParser()
p.add_argument("mode", choices=["collect", "analyze"])
p.add_argument("session")
p.add_argument("--gcc", default="gcc")
p.add_argument("--tag", default="large-pages", help="output folder name inside the session")
a = p.parse_args()
R = pathlib.Path(__file__).resolve().parents[2]
S = R / "sessions" / a.session
out = S / a.tag
src = R / "project-2-memory/src/membench.c"
# (label, bytes, stride): same-node page-locality pair plus a footprint sweep at 64 B spacing.
CASES = [
    ("packed 16,384 nodes, 64 B", 1048576, 64),
    ("scattered 16,384 nodes, 4 KiB", 67108864, 4096),
    ("4 MiB", 4194304, 64),
    ("16 MiB", 16777216, 64),
    ("64 MiB", 67108864, 64),
    ("256 MiB", 268435456, 64),
]
TRIALS = 5


def collect():
    out.mkdir(exist_ok=False)
    (out / "build").mkdir()
    shutil.copy(src, out / "membench.c")
    (out / "HYPOTHESES.md").write_text(
        """# Predictions before the large-page study (written before collection)

- 2 MiB pages cover 512 times more memory per TLB entry. The 2,048-entry L2 DTLB then reaches 4 GiB, so every footprint here should be translated without page walks.
- **Scattered chain:** with 4 KiB pages it took about 98 cycles/load against 43 for the same 16,384 nodes packed, and the counters showed 0.66 L2-DTLB misses per load. If page walks caused the gap, large pages should bring the scattered chain close to the packed one. Any remaining gap would come from 4 KiB set aliasing (every node maps to the same L1/L2 set index), which large pages do not change.
- **Footprint sweep:** small for 4 MiB (no L2-DTLB misses even with 4 KiB pages), larger for 64-256 MiB, where base pages walk on most loads. DRAM access itself remains, so large pages should reduce, not remove, the DRAM-region latency.
"""
    )
    gcc = shutil.which(a.gcc) or a.gcc
    exe = out / "build" / "membench.exe"
    cmd = [gcc, "-std=c11", "-O2", "-Wall", "-Wextra", str(src), "-o", str(exe)]
    subprocess.run(cmd, check=True)
    probe = subprocess.run(
        [str(exe), "latency", "1048576", "64", "random", "100", "0.05", "0", "4320", "large"],
        capture_output=True,
        text=True,
    )
    if probe.returncode:
        shutil.rmtree(out)  # holds only the source copy, build and hypotheses just created above
        raise SystemExit(
            "Large pages unavailable (sign out and back in after granting SeLockMemoryPrivilege): "
            + probe.stderr.strip()
        )
    env = {
        "start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "compiler": subprocess.check_output([gcc, "--version"], text=True).splitlines()[0],
        "command": [
            pathlib.Path(c).name if i in (0, len(cmd) - 3) else c for i, c in enumerate(cmd)
        ],
        "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "trials": TRIALS,
        "seconds": 1.0,
        "cpu": 0,
        "seed": 4320,
    }
    runs = [
        (c, pg, t) for c in range(len(CASES)) for pg in ["base", "large"] for t in range(TRIALS)
    ]
    random.Random(4320).shuffle(runs)
    with (out / "results.jsonl").open("x") as f:
        for i, (c, pg, t) in enumerate(runs):
            _, b, s = CASES[c]
            args = [str(exe), "latency", str(b), str(s), "random", "100", "1", "0", "4320"] + (
                ["large"] if pg == "large" else []
            )
            r = subprocess.run(args, capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(f"{args}: exit {r.returncode} {r.stderr}")
            row = json.loads(r.stdout)
            assert row["correct"] and row["pages"] == pg
            row.update(case=c, trial=t, sequence=i)
            f.write(json.dumps(row) + "\n")
            print(f"large pages {i+1}/{len(runs)}", flush=True)
    env["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / "environment.json").write_text(json.dumps(env, indent=2))


def busy_note(m):
    """Summarize the retained first attempt, collected while background apps kept the CPU 36-90% busy."""
    B = S / "large-pages-busy"
    if a.tag != "large-pages" or not (B / "results.jsonl").exists():
        return []
    G = collections.defaultdict(list)
    for r in (json.loads(l) for l in (B / "results.jsonl").read_text().splitlines()):
        G[r["case"], r["pages"]].append(r["ns_per_op"])
    rows = [
        f"| {CASES[c][0]} | {pg} | {m((c,pg))[0]:.2f} [{m((c,pg))[1]:.2f}, {m((c,pg))[2]:.2f}] | {statistics.median(G[c,pg]):.2f} [{min(G[c,pg]):.2f}, {max(G[c,pg]):.2f}] |"
        for c in [1, 2, 4]
        for pg in ["base", "large"]
    ]
    return [
        "## Benchmark pitfall: the same study on a busy machine",
        "",
        "The study was first run minutes after signing in, while background applications kept total CPU use at 36-90% (the Windows audio engine alone used about one core). That run is retained unedited in [`large-pages-busy/`](large-pages-busy/results.jsonl). Same binary, same pinning, same seed:",
        "",
        "| Condition | Pages | Quiet ns/load [min,max] | Busy ns/load [min,max] |",
        "|---|---|---|---|",
        *rows,
        "",
        "On the busy machine the scattered chain looked 2.5x slower and 64 MiB large pages looked *slower* than base pages, the opposite of the quiet result. Pinning the benchmark to CPU0 does not isolate it: other cores share the L3 and the memory controller, and an L3-resident or DRAM-bound benchmark measures their traffic too. CPU load was checked (3-11%) before the quiet run.",
        "",
    ]


def analyze():
    sys.path.insert(0, str(R / "common"))
    from charts import plot

    rows = [json.loads(l) for l in (out / "results.jsonl").read_text().splitlines()]
    env = json.loads((out / "environment.json").read_text())
    assert all(r["correct"] for r in rows) and set(
        collections.Counter((r["case"], r["pages"]) for r in rows).values()
    ) == {TRIALS}
    G = collections.defaultdict(list)
    for r in rows:
        G[r["case"], r["pages"]].append(r["ns_per_op"])
    m = lambda k: (statistics.median(G[k]), min(G[k]), max(G[k]))
    iv = lambda v: f"{v[0]:.2f} [{v[1]:.2f}, {v[2]:.2f}]"
    counters = (
        json.loads((S / "counters.json").read_text()) if (S / "counters.json").exists() else None
    )
    l2 = {}
    if counters:
        for g, c in [
            ("packed-pages", 0),
            ("scattered-pages", 1),
            ("LLC-candidate", 2),
            ("DRAM-candidate", 4),
        ]:
            v = [
                r["counters"]["LabL2DTLBMiss"]["per_op_lower"]
                for r in counters["records"]
                if r["group"] == g
            ]
            l2[c] = statistics.median(v)
    tab = []
    for c, (label, b, s) in enumerate(CASES):
        base, large = m((c, "base")), m((c, "large"))
        tab.append(
            f"| {label} | {b//1024:,} | {iv(base)} | {iv(large)} | {100*(1-large[0]/base[0]):+.1f}% | "
            + (f"{l2[c]:.3f}" if c in l2 else "-")
            + " |"
        )
    sweep = [2, 3, 4, 5]
    F = S / "figures"
    plot(
        F / "large-pages.svg",
        "Dependent random chain: 4 KiB vs 2 MiB pages",
        "Footprint (KiB, log2)",
        "ns / dependent load",
        [
            (f"{pg} pages", [(CASES[c][1] // 1024, *m((c, pg))) for c in sweep])
            for pg in ["base", "large"]
        ],
        True,
        "64 B node spacing, CPU0, 5 trials (whiskers min-max).",
    )
    pb, sb, sl, pl = m((0, "base"))[0], m((1, "base"))[0], m((1, "large"))[0], m((0, "large"))[0]
    gap_base, gap_large = sb - pb, sl - pl
    tlb_share = 1 - gap_large / gap_base if gap_base > 0 else float("nan")
    d64 = m((4, "base"))[0] - m((4, "large"))[0]
    L = [
        "# Large pages: 4 KiB versus 2 MiB",
        "",
        f"Same Ryzen 5 5500 host. Windows large pages (2 MiB, `VirtualAlloc` with `MEM_LARGE_PAGES` after enabling `SeLockMemoryPrivilege`) versus ordinary 4 KiB pages, for the same dependent random-chain benchmark (`membench.c` with the optional `large` argument). {len(rows)} runs, {TRIALS} trials per condition in a shuffled order, 1 s each, pinned to CPU0; each chain is verified as a single cycle before timing and its end position is checked after. [Predictions]({a.tag}/HYPOTHESES.md) were written before collection; [raw results]({a.tag}/results.jsonl).",
        "",
        "![Large pages](figures/large-pages.svg)",
        "",
        "| Condition | Footprint KiB | 4 KiB pages ns/load [min,max] | 2 MiB pages ns/load [min,max] | Time saved by 2 MiB pages | L2-DTLB misses/load with 4 KiB pages (counters) |",
        "|---|---:|---|---|---:|---:|",
        *tab,
        "",
        f'**Separating TLB misses from set conflicts.** With 4 KiB pages the scattered chain is {sb-pb:.1f} ns/load slower than the packed chain over the same 16,384 nodes; with 2 MiB pages the gap shrinks to {gap_large:.1f} ns. Large pages remove the page walks (0.66 per load with base pages) but keep the 4 KiB spacing, so about **{100*tlb_share:.0f}%** of the gap is attributable to translation. Treat that as a **lower bound**: the L1D is indexed by address bits inside a 4 KiB page, so it aliases equally under both page sizes, but the L2 is physically indexed. With 2 MiB pages, physically contiguous memory makes all 16,384 nodes fall into the same L2 sets, whereas scattered 4 KiB frames spread them out. Set conflicts are therefore at least as bad in the large-page run. The scattered large-page trials also vary widely ({m((1,"large"))[1]:.1f}-{m((1,"large"))[2]:.1f} ns), so the split is approximate. This narrows, but does not fully resolve, the confound from the counter analysis.',
        "",
        f"The packed chain also gains ({pb:.2f} to {pl:.2f} ns) despite having almost no L2-DTLB misses: its 256 pages overflow the 64-entry L1 DTLB (0.24 L1-DTLB misses per load in the counter run), and with 2 MiB pages one L1-DTLB entry covers the whole chain.",
        "",
        f"**Footprint sweep.** "
        + " ".join(
            f'{CASES[c][0]}: {m((c,"base"))[0]:.1f} to {m((c,"large"))[0]:.1f} ns/load'
            + (
                " (ranges do not overlap)"
                if m((c, "large"))[2] < m((c, "base"))[1] or m((c, "large"))[1] > m((c, "base"))[2]
                else " (ranges overlap: no clear difference)"
            )
            + "."
            for c in sweep
        )
        + f' At 64 MiB, base pages walked on about {l2.get(4,float("nan")):.2f} of every load. DRAM latency remains with either page size, so large pages can only remove the translation part of the DRAM-region cost. At 4 MiB, 1,024 base pages already fit the 2,048-entry L2 DTLB, so only cheaper L1-DTLB refills can be saved. **Anomaly:** 16 MiB (4,096 base pages, twice the L2-DTLB reach) shows no clear gain, while 4 MiB and 64 MiB do. The 16 MiB footprint sits at the L3 capacity, where the base-page run is noisy (one trial at 119 ns), and part of the L3 is used by other activity; more trials at 8-32 MiB would be needed to explain this.',
        "",
        *busy_note(m),
        "**Limits.** Five 1 s trials per condition; min/max ranges are not confidence intervals. Large pages were requested explicitly; Windows does not use them transparently for ordinary allocations, so this is an opt-in optimization requiring a privilege that the default account does not have. No counters were captured for the large-page runs; the TLB columns come from the earlier 4 KiB capture.",
    ]
    (S / "LARGE-PAGES.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("large-page report written")


collect() if a.mode == "collect" else analyze()
