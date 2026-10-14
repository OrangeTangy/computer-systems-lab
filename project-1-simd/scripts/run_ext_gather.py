"""Add a forced-hardware-gather build to an existing SIMD extension session.

python project-1-simd/scripts/run_ext_gather.py SESSION [--gcc gcc] [--objdump objdump]
GCC's Zen 3 tuning replaces AVX2 gathers with emulated gathers (scalar loads packed into vectors).
This build re-enables vgatherdps through -mtune-ctrl and verifies it in the disassembly before timing.
"""

import argparse, hashlib, json, pathlib, random, re, shutil, subprocess

p = argparse.ArgumentParser()
p.add_argument("session")
p.add_argument("--gcc", default="gcc")
p.add_argument("--objdump", default="objdump")
a = p.parse_args()
R = pathlib.Path(__file__).resolve().parents[2]
E = R / "sessions" / a.session / "simd-extension"
src = E / "simd_ext.c"
out = E / "results-forcegather.jsonl"
if out.exists():
    raise SystemExit("Refusing existing results-forcegather.jsonl")
env = json.loads((E / "environment.json").read_text())
assert hashlib.sha256(src.read_bytes()).hexdigest() == env["source_sha256"]
gcc = shutil.which(a.gcc) or a.gcc
objdump = shutil.which(a.objdump) or a.objdump
exe = E / "build" / "ext-float-native-forcegather.exe"
flags = ["-march=native", "-mtune-ctrl=use_gather_2parts,use_gather_4parts,use_gather_8parts"]
cmd = [
    gcc,
    "-std=c11",
    "-O3",
    "-ffp-contract=off",
    "-DTYPE=float",
    *flags,
    "-fopt-info-vec-all=" + str(E / "evidence" / "float-native-forcegather-vector.txt"),
    str(src),
    "-o",
    str(exe),
]
subprocess.run(cmd, check=True)
dis = subprocess.check_output([objdump, "-d", "--no-show-raw-insn", str(exe)], text=True)
body = re.search(r"<gather>:\n(.*?)\n\n", dis, re.S).group(1)
# Count mnemonics only; jump targets such as <gather+0x40> must not be counted.
ins = [l.split("\t")[-1].strip() for l in body.splitlines() if "\t" in l]
kern = {
    "ymm": body.count("%ymm"),
    "xmm": body.count("%xmm"),
    "gather": sum(1 for i in ins if re.match(r"v(p)?gather", i)),
    "sample": [i for i in ins if "gather" in i.split()[0]][:4],
}
assert kern["gather"] > 0, "forced build still has no hardware gather"
(E / "evidence" / "float-native-forcegather-kernels.json").write_text(
    json.dumps({"gather": kern}, indent=1)
)
env["builds"].append(
    {
        "dtype": "float",
        "variant": "native-forcegather",
        "command": [
            pathlib.Path(c).name if i in (0, len(cmd) - 3) else c for i, c in enumerate(cmd)
        ],
        "binary_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
        "kernels": {"gather": {k: kern[k] for k in ["ymm", "xmm", "gather"]}},
    }
)
(E / "environment.json").write_text(json.dumps(env, indent=2))
trials = [
    (ix, n, t)
    for ix in [0, 1]
    for n in [1024, 32768, 1048576, 16777216]
    for t in range(env["trials"])
]
random.Random(4321).shuffle(trials)
with out.open("x") as f:
    for i, (ix, n, t) in enumerate(trials):
        r = subprocess.run(
            [str(exe), str(n), "4", str(ix), "0.2"], capture_output=True, text=True, check=True
        )
        row = json.loads(r.stdout)
        row.update(dtype="float", build="native-forcegather", trial=t, sequence=i)
        f.write(json.dumps(row) + "\n")
print("forced-gather runs:", len(trials), "gathers in kernel:", kern["gather"])
