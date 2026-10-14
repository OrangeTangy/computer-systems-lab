"""Block-size, R/W-mix, data-pattern, buffering and sustained-write device-state study.

python common/collect-ssd-extension.py SESSION /path/to/fio.exe [--sustained-gib 40]
Writes only new disposable files inside sessions/SESSION/ssd-extension/scratch/ and removes
exactly those files after success. No raw device or partition is ever accepted.
About 15 minutes for the matrix plus the sustained write (bounded by --max-sustained-seconds).
"""

import argparse, datetime, json, pathlib, random, shutil, subprocess, time

p = argparse.ArgumentParser()
p.add_argument("session")
p.add_argument("fio")
p.add_argument("--sustained-gib", type=int, default=40)
p.add_argument("--max-sustained-seconds", type=int, default=900)
a = p.parse_args()
R = pathlib.Path(__file__).resolve().parents[1]
out = R / "sessions" / a.session / "ssd-extension"
out.mkdir(exist_ok=False)
fio = str(pathlib.Path(a.fio).resolve())
scratch = out / "scratch"
scratch.mkdir()
target = scratch / "disposable.bin"
sustained = scratch / "sustained.bin"
for t in [target, sustained]:
    if t.exists() or t.is_symlink():
        raise SystemExit("Refusing existing target")
need = (a.sustained_gib + 2 + 20) * 2**30  # files plus a 20 GiB margin for the OS
if shutil.disk_usage(scratch).free < need:
    raise SystemExit(f"Need at least {need/2**30:.0f} GiB free")
for d in ["raw", "configs", "logs"]:
    (out / d).mkdir()
BASE = "[global]\nioengine=windowsaio\ndirect=1\nthread=1\nnumjobs=1\ngroup_reporting=1\nrandrepeat=1\nrandseed=14320\nrefill_buffers=1\nlat_percentiles=1\nclat_percentiles=1\npercentile_list=50:95:99:99.9\n"


def capture(name, options, filename="disposable.bin", size="2G"):
    opts = {"filename": filename, "size": size, "buffer_compress_percentage": 0}
    opts.update(options)
    config = BASE + "".join(f"{k}={v}\n" for k, v in opts.items()) + f"\n[{name}]\n"
    path = out / "configs" / (name + ".fio")
    path.write_text(config)
    result = out / "raw" / (name + ".json")
    subprocess.run(
        [fio, str(path), "--output-format=json", "--output=" + str(result)], cwd=scratch, check=True
    )
    data = json.loads(result.read_text())
    assert len(data["jobs"]) == 1 and data["jobs"][0]["error"] == 0
    return data


def smart():
    # Reliability counters need elevation on this host; record the refusal instead of a value.
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PhysicalDisk | Get-StorageReliabilityCounter | Select Temperature,TemperatureMax,Wear | ConvertTo-Json",
        ],
        capture_output=True,
        text=True,
    )
    return {
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip()[:300],
        "returncode": r.returncode,
    }


metadata = {
    "start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "fio": subprocess.check_output([fio, "--version"], text=True).strip(),
    "repetitions": 3,
    "runtime_seconds": 5,
    "ramp_seconds": 2,
    "matrix_file_bytes": 2 * 2**30,
    "sustained_bytes": a.sustained_gib * 2**30,
    "max_sustained_seconds": a.max_sustained_seconds,
    "free_bytes_before": shutil.disk_usage(scratch).free,
    "numjobs": 1,
    "host_metadata": "../environment.json",
    "smart_before": smart(),
    "write_scope": f"2 GiB matrix file, 16 MiB verification, {a.sustained_gib} GiB sustained sequential write; disposable files only",
    "state": "active system drive with free space; SLC-cache behavior is observed, not configured",
}
(out / "environment.json").write_text(json.dumps(metadata, indent=2))
(out / "HYPOTHESES.md").write_text(
    """# Predictions before the SSD extension (written before collection)

- **Block size:** IOPS should fall and MB/s rise with block size until the SATA 6 Gb/s link (~550 MB/s usable) caps sequential and large random reads. Random and sequential reads should converge at large blocks because each request already covers many flash pages. Latency should grow roughly with transfer time once bandwidth-bound.
- **Read/write mix:** 4 KiB random writes land in the SLC cache and may complete faster than reads at low depth, but mixed traffic should reduce total IOPS below either pure case because reads queue behind program operations.
- **Data pattern:** the drive is not expected to compress data in its controller, so compressible and incompressible buffers should perform the same within noise. A difference would point to controller compression or a measurement artifact.
- **Buffered vs direct:** a buffered random read over a 2 GiB file that fits in 16 GiB of RAM should report far higher IOPS and microsecond latencies because it measures the OS page cache, not the SSD.
- **Sustained write:** throughput should start near the SATA ceiling while the SLC cache absorbs writes, then drop sharply (a cliff) once the cache fills, with tail latency rising. A short idle period should partially restore burst throughput as the drive folds SLC data into TLC in the background.
"""
)
capture("prepare", {"rw": "write", "bs": "1M", "iodepth": 8, "end_fsync": 1})
capture(
    "verify",
    {
        "rw": "write",
        "bs": "4k",
        "iodepth": 1,
        "size": "16M",
        "verify": "crc32c",
        "do_verify": 1,
        "verify_fatal": 1,
    },
)
cases = [
    ("blocksize", rw, bs, 32, 100 if "read" in rw else 0, 0, 1)
    for rw in ["randread", "read", "randwrite", "write"]
    for bs in [4, 16, 32, 64, 128, 256]
]
cases += [("mix", "randrw", 4, 32, m, 0, 1) for m in [100, 70, 50, 0]]
cases += [("pattern", "write", 128, 32, 0, c, 1) for c in [0, 50, 90]]
cases += [("buffering", "randread", 4, 1, 100, 0, d) for d in [0, 1]]
trials = [(c, t) for c in cases for t in range(3)]
random.Random(4320).shuffle(trials)
with (out / "index.jsonl").open("x") as f:
    for i, ((study, rw, bs, qd, readpct, compress, direct), trial) in enumerate(trials):
        name = f"{i:03}-{study}-{rw}-{bs}k-qd{qd}-r{readpct}-c{compress}-d{direct}-t{trial}"
        begin = time.time()
        opts = {
            "rw": rw,
            "bs": f"{bs}k",
            "iodepth": qd,
            "time_based": 1,
            "runtime": 5,
            "ramp_time": 2,
            "buffer_compress_percentage": compress,
            "direct": direct,
        }
        if rw == "randrw":
            opts["rwmixread"] = readpct
        capture(name, opts)
        f.write(
            json.dumps(
                dict(
                    name=name,
                    study=study,
                    rw=rw,
                    bs_kib=bs,
                    qd=qd,
                    read_percent=readpct,
                    compress_percent=compress,
                    direct=direct,
                    trial=trial,
                    sequence=i,
                    start_unix=begin,
                )
            )
            + "\n"
        )
        f.flush()
        print(f"SSD extension matrix: {i+1}/{len(trials)}", flush=True)
# Device state: one long sequential write with 1 s throughput/latency logs, then an idle-recovery burst.
metadata["smart_before_sustained"] = smart()
metadata["sustained_start_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
log = lambda n: {"write_bw_log": n, "write_lat_log": n, "log_avg_msec": 1000}
capture(
    "sustained-write",
    {
        "rw": "write",
        "bs": "128k",
        "iodepth": 32,
        "runtime": a.max_sustained_seconds,
        **log("sustained"),
    },
    "sustained.bin",
    f"{a.sustained_gib}G",
)
metadata["sustained_end_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
capture(
    "post-sustained-burst",
    {"rw": "write", "bs": "128k", "iodepth": 32, "time_based": 1, "runtime": 20, **log("post")},
)
time.sleep(120)
capture(
    "after-idle-burst",
    {"rw": "write", "bs": "128k", "iodepth": 32, "time_based": 1, "runtime": 20, **log("idle")},
)
metadata["smart_after"] = smart()
for logfile in scratch.glob("*.log"):
    shutil.move(str(logfile), out / "logs" / logfile.name)
# Exact created files only; no recursive cleanup or arbitrary path accepted.
target.unlink()
sustained.unlink()
metadata["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
metadata["test_files_removed"] = True
(out / "environment.json").write_text(json.dumps(metadata, indent=2))
print("Disposable SSD files removed.", flush=True)
