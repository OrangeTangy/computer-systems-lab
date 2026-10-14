"""Validate matrix coverage, units, provenance and SSD data for a completed session."""

import collections
import hashlib
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SESSION = ROOT / "sessions" / sys.argv[1]


def load_jsonl(name):
    return [json.loads(line) for line in (SESSION / name).read_text().splitlines()]


def load_json(name):
    return json.loads((SESSION / name).read_text())


def close(a, b):
    return math.isclose(a, b, abs_tol=0.001)


def check_matrix(name, keys, total):
    """Every condition has exactly trials 0-4, all runs validated, sequence numbers complete."""
    rows = load_jsonl(name)
    assert len(rows) == total, (name, len(rows), total)
    assert all(r["correct"] for r in rows)
    assert sorted(r["sequence"] for r in rows) == list(range(total))
    trials = collections.defaultdict(set)
    for r in rows:
        trials[tuple(r[k] for k in keys)].add(r["trial"])
    assert all(t == set(range(5)) for t in trials.values())
    counts = collections.Counter(tuple(r[k] for k in keys) for r in rows)
    assert set(counts.values()) == {5}
    return rows


simd = check_matrix("simd.jsonl", ["dtype", "build", "kind", "n", "stride", "offset_elements"], 840)
for r in simd:
    elements = r["n"] * r["reps"]
    flops = 1 if r["kind"] == 1 else 2
    assert r["max_error"] <= r["tolerance"]
    assert close(r["ns_element"], r["seconds"] * 1e9 / elements)
    assert close(r["gflops"], elements * flops / r["seconds"] / 1e9)

bandwidth = check_matrix("bandwidth.jsonl", ["n"], 10)
for r in bandwidth:
    assert close(r["useful_GB_s"], 12 * r["n"] * r["passes"] / r["seconds"] / 1e9)

latency = check_matrix("latency.jsonl", ["bytes", "pattern"], 210)
for r in latency:
    assert r["pinned"] and r["cpu"] == 0
    assert close(r["ns_per_op"], r["elapsed_s"] * 1e9 / r["operations"])

loaded = check_matrix("loaded.jsonl", ["workers", "read_percent"], 105)
for r in loaded:
    assert close(r["latency_ns"], r["probe_seconds"] * 1e9 / r["loads"])

# the probe and each load worker must be on a different physical core
env = load_json("environment.json")
load_env = load_json("load-environment.json")
cores = env["cores"]["physical_cores"]
masks = []
for cpu in [0, *load_env["worker_cpus"]]:
    masks.append(next(c["logical_cpu_mask"] for c in cores if c["logical_cpu_mask"] & (1 << cpu)))
assert len(set(masks)) == len(masks)

# the saved source snapshots must be exactly what was compiled
for build in load_json("builds.json"):
    src = SESSION / "sources" / pathlib.Path(build["command"][-3]).name
    assert hashlib.sha256(src.read_bytes()).hexdigest() == build["source_sha256"], str(src)
loaded_src = (SESSION / "sources/loaded-followup.c").read_bytes()
assert hashlib.sha256(loaded_src).hexdigest() == load_env["source_sha256"]

# SSD queue-depth study: 13 conditions x 5 trials, all direct I/O and error-free
index = load_jsonl("ssd/index.jsonl")
assert len(index) == 65
assert len({r["name"] for r in index}) == 65
ssd_counts = collections.Counter((r["study"], r["rw"], r["bs_kib"], r["qd"]) for r in index)
assert set(ssd_counts.values()) == {5}
assert {r["qd"] for r in index if r["study"] == "queue"} == {1, 2, 4, 8, 16, 32, 64, 128, 256}
for row in index:
    raw = load_json("ssd/raw/" + row["name"] + ".json")
    job = raw["jobs"][0]
    assert job["error"] == 0
    stats = job["read" if "read" in row["rw"] else "write"]
    assert stats["total_ios"] > 0 and stats["bw_bytes"] > 0
    for p in ["50.000000", "95.000000", "99.000000", "99.900000"]:
        assert float(stats["lat_ns"]["percentile"][p]) > 0
    # fio 3.43 puts [global] options under "global options", per-job overrides under "job options"
    direct = job.get("job options", {}).get("direct", raw["global options"].get("direct", 0))
    assert int(direct) == 1
for name in ["prepare", "verify"]:
    assert all(j["error"] == 0 for j in load_json("ssd/raw/" + name + ".json")["jobs"])
assert load_json("ssd/environment.json")["test_file_removed"]
assert not (SESSION / "ssd/scratch/disposable.bin").exists()

print(
    "PASS: 840 SIMD, 10 matched-bandwidth, 210 latency, 105 load and 65 SSD trials;"
    " units, correctness, matrices, source hashes and file cleanup."
)
