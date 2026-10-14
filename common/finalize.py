"""Add the interpretation section to the Intel SSD results and refresh the integrity manifest.

Run after analyze_all.py, which rewrites project-3-ssd/RESULTS.md without this section.
"""

import json
import pathlib
import statistics
import subprocess
import sys

from charts import plot

ROOT = pathlib.Path(__file__).resolve().parents[1]
SSD = ROOT / "project-3-ssd"

rows = json.loads((SSD / "data/processed.json").read_text())

# median IOPS and latency per queue depth
curve = []
for qd in sorted({r["qd"] for r in rows if r["study"] == "queue"}):
    runs = [r for r in rows if r["study"] == "queue" and r["qd"] == qd]
    iops = statistics.median(r["iops"] for r in runs)
    latency = statistics.median(r["mean_lat_us"] for r in runs)
    curve.append((qd, iops, latency))
peak = max(iops for _, iops, _ in curve)
knee = next(qd for qd, iops, _ in curve if iops >= 0.9 * peak)

notes = [
    "",
    "## Interpretation and variability",
    "",
    f"The tested-range maximum median is {peak:,.0f} IOPS. The 90% operational threshold first"
    f" occurs at QD{knee}. QD128/256 were collected as a follow-up after a new file prefill, so a"
    " change at that boundary can reflect device-state drift as well as queue depth. A noisy or"
    " non-monotonic curve is not a clean saturation proof.",
    "",
]
for direct in [0, 1]:
    runs = [r for r in rows if r["study"] == "pitfall" and r["direct"] == direct]
    iops = statistics.median(r["iops"] for r in runs)
    latency = statistics.median(r["mean_lat_us"] for r in runs)
    notes.append(
        f"For the 64 MiB pitfall comparison, direct={direct} produced a median {iops:,.0f} IOPS"
        f" and {latency:.2f} us mean latency. OS caching changes what the experiment measures; a"
        " performance increase is not guaranteed for every access pattern or run."
    )
notes += [
    "",
    "Three repetitions show variation but do not robustly characterize rare events or steady"
    " state. The nearly full, active system SSD and short time windows are material limitations."
    " Completion latency includes the host/engine path and is not raw NAND access time.",
    "",
]

log = SSD / "data/raw/device-state_bw.1.log"
if log.exists():
    points = []
    for line in log.read_text().splitlines():
        msec, kib_per_s = line.split(",")[:2]
        points.append((float(msec) / 1000, float(kib_per_s) * 1024 / 1e6))
    plot(
        SSD / "figures/device-state.svg",
        "SSD short sequential-write observation",
        "Elapsed time (s)",
        "MB/s",
        [("One-second windows", [(x, y, y, y) for x, y in points])],
        notes="Single 12-second observation; no variability whiskers or steady-state claim.",
        subtitle="Measured bandwidth per logging window within one run; not repeated-trial medians",
    )
    low = min(y for _, y in points)
    high = max(y for _, y in points)
    notes.append(
        f"The one-second write-bandwidth samples ranged from {low:.2f} to {high:.2f} MB/s over"
        " this short observation. No temperature or SLC-exhaustion evidence is available. The log"
        " alone cannot identify the cause of rate changes."
    )

results = SSD / "RESULTS.md"
report = results.read_text(encoding="utf-8").split("\n## Interpretation and variability")[0].rstrip()
results.write_text(report + "\n" + "\n".join(notes), encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "common/refresh_manifest.py")], check=True)
print(f"SSD maximum median {peak:.0f} IOPS; operational knee QD{knee}.")
