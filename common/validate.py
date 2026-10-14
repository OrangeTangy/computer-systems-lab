"""Validate retained measurements and local Markdown links without rerunning benchmarks."""

import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def close(a, b):
    return abs(a - b) < 0.002


# Project 1: SIMD trials, 3 per condition
simd = load_jsonl(ROOT / "project-1-simd/data/raw.jsonl")
assert len(simd) == 450
assert all(r["correct"] for r in simd)
assert all(r["max_error"] <= r["tolerance"] for r in simd)
assert all(close(r["ns_element"], r["seconds"] * 1e9 / (r["n"] * r["reps"])) for r in simd)
conditions = collections.Counter(
    (r["dtype"], r["build"], r["kind"], r["n"], r["stride"], r["offset_elements"]) for r in simd
)
assert set(conditions.values()) == {3}

# Project 2: extended memory runs
memory = load_jsonl(ROOT / "project-2-memory/data/extended.jsonl")
assert len(memory) == 90
assert all(r["correct"] for r in memory)
assert all(close(r["latency_ns"], r["probe_seconds"] * 1e9 / r["loads"]) for r in memory)

# Project 2: controlled-load follow-up, if present
controlled_path = ROOT / "project-2-memory/data/controlled/raw.jsonl"
controlled = load_jsonl(controlled_path) if controlled_path.exists() else []
if controlled:
    assert len(controlled) == 85
    assert all(r["correct"] for r in controlled)
    counts = collections.Counter((r["workers"], r["read_percent"], r["delay_us"]) for r in controlled)
    assert len(counts) == 17 and set(counts.values()) == {5}
    for r in controlled:
        assert r["workers"] in [0, 3]
        assert r["start_lag_us"] >= 0 and r["end_overhang_us"] >= 0
        assert close(r["latency_ns"], r["probe_seconds"] * 1e9 / r["loads"])

    # probe (CPU 0) and the three workers must be on four different physical cores
    masks = json.loads((ROOT / "common/core-masks.json").read_text(encoding="utf-8-sig"))
    cores = masks["physical_cores"]
    used = []
    for cpu in [0, 2, 4, 6]:
        used.append(next(c["logical_cpu_mask"] for c in cores if c["logical_cpu_mask"] & (1 << cpu)))
    assert len(set(used)) == 4

# Project 3: every fio run finished without error and did some I/O
ssd = ROOT / "project-3-ssd"
index = load_jsonl(ssd / "data/index.jsonl")
assert len(index) >= 129
assert len({r["name"] for r in index}) == len(index)
for row in index:
    job = json.loads((ssd / "data/raw" / (row["name"] + ".json")).read_text())["jobs"][0]
    assert job["error"] == 0
    assert job["read"]["total_ios"] + job["write"]["total_ios"] > 0
for name in ["prepare", "verify", "device-state"]:
    jobs = json.loads((ssd / "data/raw" / (name + ".json")).read_text())["jobs"]
    assert all(j["error"] == 0 for j in jobs)

# relative links in the Markdown files must point at files that exist
broken = []
for md in ROOT.rglob("*.md"):
    for link in re.findall(r"\]\(([^)]+)\)", md.read_text(encoding="utf-8")):
        if "://" in link or link.startswith("#"):
            continue
        target = link.split("#")[0]
        if target and not (md.parent / target).exists():
            broken.append((str(md.relative_to(ROOT)), link))
assert not broken, broken

print(
    f"PASS: {len(simd)} SIMD + {len(memory)} extended memory + {len(controlled)} controlled memory"
    f" + {len(index)} SSD trials, correctness/unit checks, core placement, expected conditions,"
    " all local Markdown links."
)
