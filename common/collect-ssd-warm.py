"""Warm-page-cache companion to the buffered-vs-direct pitfall in the SSD extension.

python common/collect-ssd-warm.py SESSION /path/to/fio.exe
Creates one new 2 GiB disposable file, reads it once with buffered I/O so Windows caches it,
then runs three buffered 4 KiB random-read QD1 trials. Deletes exactly that file afterwards.
"""

import json, pathlib, shutil, subprocess, sys, time

R = pathlib.Path(__file__).resolve().parents[1]
X = R / "sessions" / sys.argv[1] / "ssd-extension"
fio = str(pathlib.Path(sys.argv[2]).resolve())
index = X / "warm-index.jsonl"
scratch = X / "scratch"
scratch.mkdir(exist_ok=True)
target = scratch / "warm.bin"
if index.exists() or target.exists():
    raise SystemExit("Refusing existing warm study or target")
if shutil.disk_usage(scratch).free < 24 * 2**30:
    raise SystemExit("Need at least 24 GiB free")
BASE = "[global]\nioengine=windowsaio\nthread=1\nnumjobs=1\ngroup_reporting=1\nfilename=warm.bin\nsize=2G\nrandrepeat=1\nrandseed=14320\nrefill_buffers=1\nbuffer_compress_percentage=0\nlat_percentiles=1\nclat_percentiles=1\npercentile_list=50:95:99:99.9\n"


def capture(name, opts):
    path = X / "configs" / (name + ".fio")
    path.write_text(BASE + "".join(f"{k}={v}\n" for k, v in opts.items()) + f"\n[{name}]\n")
    out = X / "raw" / (name + ".json")
    subprocess.run(
        [fio, str(path), "--output-format=json", "--output=" + str(out)], cwd=scratch, check=True
    )
    assert json.loads(out.read_text())["jobs"][0]["error"] == 0


capture("warm-prepare", {"rw": "write", "bs": "1M", "iodepth": 8, "direct": 1, "end_fsync": 1})
capture(
    "warm-preread", {"rw": "read", "bs": "1M", "iodepth": 1, "direct": 0}
)  # buffered pass populates the page cache
with index.open("x") as f:
    for t in range(3):
        name = f"warm-buffered-randread-4k-qd1-t{t}"
        begin = time.time()
        capture(
            name,
            {
                "rw": "randread",
                "bs": "4k",
                "iodepth": 1,
                "direct": 0,
                "time_based": 1,
                "runtime": 5,
                "ramp_time": 2,
            },
        )
        f.write(json.dumps({"name": name, "trial": t, "start_unix": begin}) + "\n")
target.unlink()
print("Warm-cache study done; disposable file removed.")
