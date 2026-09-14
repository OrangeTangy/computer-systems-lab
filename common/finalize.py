"""Finalize findings and integrity metadata after all measurement processes finish."""
import pathlib,json,statistics,hashlib,datetime,platform
from charts import plot
R=pathlib.Path(__file__).resolve().parents[1];P=R/'project-3-ssd'
rows=json.loads((P/'data/processed.json').read_text())
curve=[]
for q in sorted({r['qd'] for r in rows if r['study']=='queue'}):
 rs=[r for r in rows if r['study']=='queue' and r['qd']==q];curve.append((q,statistics.median(r['iops'] for r in rs),statistics.median(r['mean_lat_us'] for r in rs)))
peak=max(v[1] for v in curve);knee=next(q for q,io,lat in curve if io>=.9*peak)
notes=['','## Interpretation and variability','',f'The tested-range maximum median is {peak:,.0f} IOPS. The 90% operational threshold first occurs at QD{knee}. QD128/256 were collected as a follow-up after a new file prefill, so a change at that boundary can reflect device-state drift as well as queue depth. A noisy or non-monotonic curve is not a clean saturation proof.','']
for direct in [0,1]:
 rs=[r for r in rows if r['study']=='pitfall' and r['direct']==direct]
 notes.append(f'For the 64 MiB pitfall comparison, direct={direct} produced a median {statistics.median(r["iops"] for r in rs):,.0f} IOPS and {statistics.median(r["mean_lat_us"] for r in rs):.2f} us mean latency. OS caching changes what the experiment measures; a performance increase is not guaranteed for every access pattern or run.')
notes+=['','Three repetitions show variation but do not robustly characterize rare events or steady state. The nearly full, active system SSD and short time windows are material limitations. Completion latency includes the host/engine path and is not raw NAND access time.','']
log=P/'data/raw/device-state_bw.1.log'
if log.exists():
 points=[]
 for line in log.read_text().splitlines():
  v=line.split(',');points.append((float(v[0])/1000,float(v[1])*1024/1e6))
 plot(P/'figures/device-state.svg','SSD short sequential-write observation','Elapsed time (s)','MB/s',[('One-second windows',[(x,y,y,y) for x,y in points])],notes='Single 12-second observation; no variability whiskers or steady-state claim.',subtitle='Measured bandwidth per logging window within one run; not repeated-trial medians')
 notes.append(f'The one-second write-bandwidth samples ranged from {min(y for x,y in points):.2f} to {max(y for x,y in points):.2f} MB/s over this short observation. No temperature or SLC-exhaustion evidence is available. The log alone cannot identify the cause of rate changes.')
(P/'RESULTS.md').write_text((P/'RESULTS.md').read_text()+'\n'.join(notes))
readme=R/'README.md';text=readme.read_text(encoding='utf-8');text=text.replace('| SSD results | More requests can help until the line gets too long | See the generated [same-run throughput/latency table](project-3-ssd/RESULTS.md); distinguish the measured range from sustained device limits |',f'| SSD queue sweep: maximum tested median **{peak:,.0f} IOPS**, 90% threshold at **QD{knee}** | More requests can help until the line gets too long | The curve is variable and high-QD points are a supplemental session; [see the actual table](project-3-ssd/RESULTS.md) |');readme.write_text(text,encoding='utf-8')
files={str(p.relative_to(R)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in R.rglob('*') if p.is_file() and not any(part in ['.git','build','__pycache__','scratch','counter-captures'] for part in p.relative_to(R).parts) and p.name!='sha256.json'}
(R/'common/sha256.json').write_text(json.dumps(files,indent=2))
(R/'common/collection-notes.json').write_text(json.dumps({'platform':platform.platform(),'python':platform.python_version(),'notes':['All measured new kernels ran natively on Windows.','Three suites run sequentially; assistant file editing/tool queries and normal OS activity may occur during runs.','No exclusive isolation; Balanced power policy.','WPR capture failed with access denied; no counter trace exists.','Storage reliability query failed with CIM access unavailable.','Approximately 25 GB free before 2 GiB SSD file allocation.','Supplemental high-QD session separately labeled.']},indent=2))
print(f'SSD maximum median {peak:.0f} IOPS; operational knee QD{knee}.')
