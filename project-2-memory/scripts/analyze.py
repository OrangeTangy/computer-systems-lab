"""Summarize one run and draw standalone SVG figures; uses Python standard library."""
import collections,json,pathlib,statistics,sys,math,html
ROOT=pathlib.Path(__file__).resolve().parents[1]
run=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else sorted((ROOT/'data/raw').glob('pilot-*'))[-1]
rows=[json.loads(line) for line in (run/'measurements.jsonl').read_text().splitlines()]
groups=collections.defaultdict(list)
for r in rows:groups[tuple(r[k] for k in ['mode','pattern','bytes','stride','reads_percent'])].append(r)
summary=[]
for key,rs in sorted(groups.items()):
    s=dict(zip(['mode','pattern','bytes','stride','reads_percent'],key));s['n']=len(rs)
    for metric in ['ns_per_op','useful_GiB_s']:
        v=[r[metric] for r in rs]
        s[metric]={'median':statistics.median(v),'min':min(v),'max':max(v),'stdev':statistics.stdev(v) if len(v)>1 else None}
    summary.append(s)
out=ROOT/'data/processed'/run.name;out.mkdir(parents=True,exist_ok=True)
(out/'summary.json').write_text(json.dumps(summary,indent=2))
fig=ROOT/'figures'/run.name;fig.mkdir(parents=True,exist_ok=True)
def plot(name,title,series,metric,ylabel):
    colors=['#2563eb','#dc2626','#059669','#9333ea','#ea580c','#0891b2']
    allr=[r for _,rs in series for r in rs]
    xmin=min(math.log2(r['bytes']) for r in allr);xmax=max(math.log2(r['bytes']) for r in allr)
    ymax=max(r[metric]['max'] for r in allr)*1.12
    def x(v):return 95+(math.log2(v)-xmin)/(xmax-xmin)*700
    def y(v):return 430-v/ymax*325
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="580" viewBox="0 0 1000 580">',
           '<rect width="1000" height="580" fill="white"/>','<g font-family="Arial,sans-serif" fill="#172033">',
           f'<text x="45" y="35" font-size="23">{html.escape(title)}</text>',
           '<text x="45" y="62" font-size="14">PRELIMINARY Windows pilot | median; whiskers show trial min-max</text>',
           f'<text x="95" y="92" font-size="14">{html.escape(ylabel)}</text>']
    for i in range(6):
        val=ymax*i/5;yy=y(val)
        parts += [f'<path d="M95 {yy} H795" stroke="#e2e8f0"/>',f'<text x="82" y="{yy+5}" text-anchor="end" font-size="12">{val:.2g}</text>']
    for exp in sorted(set(int(math.log2(r['bytes'])) for r in allr)):
        val=2**exp;label=f'{val//1024} KiB' if val<1048576 else f'{val//1048576} MiB'
        parts.append(f'<text x="{x(val)}" y="453" text-anchor="middle" font-size="12">{label}</text>')
    for j,(label,rs) in enumerate(series):
        color=colors[j%len(colors)];rs=sorted(rs,key=lambda r:r['bytes'])
        points=' '.join(f'{x(r["bytes"])},{y(r[metric]["median"])}' for r in rs)
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
        for r in rs:
            xx=x(r['bytes']);lo=y(r[metric]['min']);hi=y(r[metric]['max'])
            parts += [f'<path d="M{xx} {hi} V{lo} M{xx-4} {hi} H{xx+4} M{xx-4} {lo} H{xx+4}" stroke="{color}"/>',f'<circle cx="{xx}" cy="{y(r[metric]["median"])}" r="3" fill="{color}"/>']
        parts.append(f'<text x="815" y="{120+24*j}" font-size="12" fill="{color}">{html.escape(label)}</text>')
    parts += ['<text x="445" y="485" text-anchor="middle" font-size="15">Allocated footprint (log2 scale)</text>',
              '<text x="45" y="520" font-size="13">No cache boundaries assigned yet. Affinity controls migration, not frequency or background load.</text>',
              '<text x="45" y="543" font-size="13">Bandwidth is useful 8-byte accesses / second, not measured memory-controller traffic.</text>','</g></svg>']
    (fig/name).write_text('\n'.join(parts))
plot('latency.svg','Dependent-load latency versus footprint',[(f'{pat}, {stride} B',[r for r in summary if r['mode']=='latency' and r['pattern']==pat and r['stride']==stride]) for pat in ['sequential','random'] for stride in [64,256,1024]],'ns_per_op','Nanoseconds / dependent load')
plot('bandwidth.svg','Sequential useful throughput versus footprint',[(f'{pct}% reads',[r for r in summary if r['mode']=='bandwidth' and r['stride']==8 and r['reads_percent']==pct]) for pct in [0,50,70,100]],'useful_GiB_s','Useful GiB/s; scalar mixed-operation kernel')
report=['# Pilot observations','',f'Source run: `{run.name}`. {len(rows)} successful trials; {len(summary)} conditions.','',
        'These are preliminary measurements, not final per-cache latency claims. Error whiskers are min-max, not confidence intervals.','',
        '| Footprint | Random 64 B dependent-load median (ns) | Sequential 64 B median (ns) |','|---|---:|---:|']
for n in sorted(set(r['bytes'] for r in summary)):
    match=lambda pat: next(r['ns_per_op']['median'] for r in summary if r['mode']=='latency' and r['pattern']==pat and r['stride']==64 and r['bytes']==n)
    report.append(f'| {n//1024:,} KiB | {match("random"):.2f} | {match("sequential"):.2f} |')
report += ['', 'Interpretation: a regular dependent chain can still benefit from hardware prefetching. The random chain reduces predictability. Large random footprints may include TLB/page-walk costs as well as DRAM latency.', '',
           'Do not infer peak DRAM bandwidth from this scalar single-thread kernel. Mix percentages describe operations (last partial group can differ slightly), not physical bus read/write ratios. Strided tests touch only one 8-byte value per selected location; allocation size alone is not cache occupancy.', '',
           'Still required: verified core/cache topology and final environment, sustained/loaded latency and concurrency experiments, hardware cache/TLB counters, page-locality experiments, and the completed report.']
(out/'observations.md').write_text('\n'.join(report))
print(out);print(fig)
