"""Collect a separate, immutable Windows session; never replace historical data.

Usage: python common/collect-followup.py --session ryzen-20261014
GCC/objdump must be on PATH. Suites are sequential, with five interleaved repeats.
"""

import argparse, datetime, hashlib, json, os, pathlib, platform, random, shutil, subprocess

R = pathlib.Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--session", required=True)
a = p.parse_args()
if not a.session or any(
    c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in a.session
):
    p.error("Use a simple session name")
out = R / "sessions" / a.session
out.mkdir(parents=True, exist_ok=False)
build = out / "build"
build.mkdir()
(out / "sources").mkdir()
(out / "evidence").mkdir()


def run(cmd):
    return subprocess.check_output(
        [str(x) for x in cmd], text=True, encoding="utf-8", errors="replace"
    )


def save(name, obj):
    (out / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def compile(source, name, flags=()):
    src = R / source
    shutil.copy2(src, out / "sources" / src.name)
    exe = build / (name + ".exe")
    cmd = ["gcc", "-std=c11", "-O3", "-Wall", "-Wextra", *flags, str(src), "-o", str(exe)]
    result = subprocess.run(cmd, text=True, capture_output=True)
    (out / "evidence" / (name + "-build.txt")).write_text(result.stdout + result.stderr)
    result.check_returncode()
    builds.append(
        {
            "name": name,
            "command": cmd,
            "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
            "binary_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
        }
    )
    return exe


builds = []
top = compile("common/topology.c", "topology")
cores = compile("common/core_masks.c", "core-masks")
import winreg

with winreg.OpenKey(
    winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
) as k:
    cpu = winreg.QueryValueEx(k, "ProcessorNameString")[0]
env = {
    "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "cpu": cpu,
    "os": platform.platform(),
    "python": platform.python_version(),
    "compiler": run(["gcc", "--version"]),
    "topology": json.loads(run([top])),
    "cores": json.loads(run([cores])),
    "policy": run(["powercfg", "/getactivescheme"]),
    "repetitions": 5,
    "cpu_pinned": 0,
    "isolation": "affinity only; no exclusive reservation",
    "frequency": "not fixed; no measured core-clock claim",
    "numa": "default first touch on pinned thread; no explicit NUMA binding",
    "page_policy": "ordinary 4 KiB allocation; large-page availability recorded by topology probe",
}
save("environment.json", env)
shutil.copy2(__file__, out / "sources" / pathlib.Path(__file__).name)
(out / "HYPOTHESES.md").write_text(
    "# Predictions recorded before collection\n\nWider SIMD should help cache-resident independent loops; large arrays should compress its advantage. Ordered dot can fail to benefit. A two-read/one-write stream should better match AXPY traffic than a read-only proxy, but remains an empirical reference. Random dependent-load latency should rise around reported capacities; exact attribution needs counters. More homogeneous physical-core workers should increase contention, eventually yielding diminishing throughput returns; a plateau is not guaranteed. These are predictions, not measurements.\n"
)
variants = {}
flags = {
    "scalar": ["-fno-tree-vectorize", "-ffp-contract=off"],
    "auto": ["-ffp-contract=off"],
    "native": ["-march=native", "-ffp-contract=off"],
}
for dtype in ["float", "double"]:
    for b, f in flags.items():
        tag = dtype + "-" + b
        variants[dtype, b] = compile(
            "project-1-simd/src/simd.c",
            tag,
            [
                *f,
                "-DTYPE=" + dtype,
                "-fopt-info-vec-all=" + str(out / "evidence" / (tag + "-vector.txt")),
            ],
        )
        (out / "evidence" / (tag + "-assembly.txt")).write_text(
            run(["objdump", "-d", variants[dtype, b]])
        )
cases = set()
for dtype in ["float", "double"]:
    for b in flags:
        for kind in range(3):
            for n in [1024, 8192, 65536, 524288, 4194304, 16777216]:
                cases.add((dtype, b, kind, n, 1, 0))
        for n in [16, 19, 65536, 65539]:
            for offset in [0, 1]:
                cases.add((dtype, b, 0, n, 1, offset))
        for stride in [2, 4, 8]:
            cases.add((dtype, b, 1, 524288, stride, 0))


def collect(name, cases, command):
    trials = [(c, t) for c in sorted(cases) for t in range(5)]
    random.Random(14320).shuffle(trials)
    with (out / name).open("x", encoding="utf-8") as f:
        for i, (c, t) in enumerate(trials):
            cmd, meta = command(c)
            row = json.loads(run(cmd))
            assert row["correct"]
            row.update(meta, trial=t, sequence=i)
            f.write(json.dumps(row) + "\n")
            f.flush()
            if i % 40 == 0:
                print(f"{name}: {i+1}/{len(trials)}", flush=True)


collect(
    "simd.jsonl",
    cases,
    lambda c: (
        [variants[c[0], c[1]], c[3], c[4], c[5], c[2], 0.15],
        {"dtype": c[0], "build": c[1]},
    ),
)
bw = compile("common/followup-bandwidth.c", "bandwidth", ["-mavx2"])
collect("bandwidth.jsonl", [(n,) for n in [4194304, 16777216]], lambda c: ([bw, c[0]], {}))
mem = compile("project-2-memory/src/membench.c", "memory")
# Dense spacing around the actual host capacities, rather than assigning Intel boundaries.
sizes = [
    4096,
    16384,
    24576,
    32768,
    49152,
    65536,
    131072,
    262144,
    393216,
    524288,
    786432,
    1048576,
    2097152,
    4194304,
    8388608,
    12582912,
    16777216,
    25165824,
    33554432,
    67108864,
    134217728,
]
collect(
    "latency.jsonl",
    [(n, pat) for n in sizes for pat in ["random", "sequential"]],
    lambda c: ([mem, "latency", c[0], 64, c[1], 100, 0.2, 0, 4320], {}),
)
save("builds.json", builds)
print(f"Saved separate session: {out}", flush=True)
