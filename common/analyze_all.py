import pathlib,json,statistics,collections,sys
from charts import plot
R=pathlib.Path(__file__).resolve().parents[1]
def load(p):return [json.loads(s) for s in p.read_text().splitlines()]
def stats(v):return [statistics.median(v),min(v),max(v)]
def group(rows,keys,metric):
 g=collections.defaultdict(list)
 for r in rows:g[tuple(r[k] for k in keys)].append(r[metric])
 return {k:stats(v) for k,v in sorted(g.items())}
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(x) for x in row)+' |' for row in rows])
P=R/'project-1-simd';rows=load(P/'data/raw.jsonl');g=group(rows,['dtype','build','kind','n','stride','offset_elements'],'ns_element');through=group(rows,['dtype','build','kind','n','stride','offset_elements'],'gflops')
names=['AXPY (out of place)','Multiply','Dot product'];sizes=[1024,8192,65536,524288,4194304]
findings=[]
for dtype in ['float','double']:
 for kind in range(3):
  series=[]
  for build in ['auto','native']:
   ps=[]
   for n in sizes:
    base=g[dtype,'scalar',kind,n,1,0];v=g[dtype,build,kind,n,1,0];ps.append((n,base[0]/v[0],base[1]/v[2],base[2]/v[1]))
   series.append((build,ps))
  plot(P/f'figures/{dtype}-{kind}-speedup.svg',f'{names[kind]}: {dtype} SIMD speedup','Elements N (log2)','Scalar time / build time',series,True,'Whiskers are conservative ratios of trial extrema; no pairing assumed.')
  series=[(build,[(n,*through[dtype,build,kind,n,1,0]) for n in sizes]) for build in ['scalar','auto','native']]
  plot(P/f'figures/{dtype}-{kind}-throughput.svg',f'{names[kind]}: {dtype} throughput','Elements N (log2)','GFLOP/s',series,True)
  width=4 if dtype=='float' else 8;arrays=2 if kind==2 else 3
  plot(P/f'figures/{dtype}-{kind}-locality.svg',f'{names[kind]}: {dtype} working-set sweep','Useful array footprint (KiB, log2)','GFLOP/s',[(b,[(n*width*arrays/1024,*through[dtype,b,kind,n,1,0]) for n in sizes]) for b in ['scalar','auto','native']],True,'Capacity markers are reported CPU0 caches, not guarantees that a point resides entirely in that cache.',[(48,'L1D'),(1280,'L2'),(12288,'LLC')])
  for n in [1024,4194304]:findings.append([dtype,names[kind],n,round(g[dtype,'scalar',kind,n,1,0][0]/g[dtype,'native',kind,n,1,0][0],2),round(through[dtype,'native',kind,n,1,0][0],2)])
detail=[]
for dtype in ['float','double']:
 for n in [16,19,65536,65539]:
  for offset in [0,1]:detail.append([dtype,n,offset,*[round(g[dtype,b,0,n,1,offset][0],3) for b in ['scalar','auto','native']]])
stride=[]
for dtype in ['float','double']:
 for s in [1,2,4,8]:stride.append([dtype,s,*[round(g[dtype,b,1,524288,s,0][0],3) for b in ['scalar','auto','native']]])
(P/'data/summary.json').write_text(json.dumps([dict(dtype=k[0],build=k[1],kind=k[2],n=k[3],stride=k[4],offset=k[5],ns_element_median=v[0],ns_element_min=v[1],ns_element_max=v[2]) for k,v in g.items()],indent=2))
sections=['# SIMD measured results','',f'{len(rows)} trials. Three trials per condition. CPU 0 pinned; Balanced power policy; background system activity uncontrolled.','',table(['Type','Kernel','N','Native speedup','Native GFLOP/s'],findings),'','## Alignment and tails','',table(['Type','N','Offset (elements)','Scalar ns/element','Auto ns/element','Native ns/element'],detail),'','## Stride study: multiply, N=524288','',table(['Type','Stride','Scalar ns/element','Auto ns/element','Native ns/element'],stride)]
(P/'RESULTS.md').write_text('\n'.join(sections))
P=R/'project-2-memory';rows=load(P/'data/extended.jsonl');g=group(rows,['study','workers','read_percent','nodes','stride'],'latency_ns');bw=group(rows,['study','workers','read_percent','nodes','stride'],'traffic_GB_s')
tab=[];series=[]
for read in [0,50,70,100]:
 ps=[]
 for w in [0,1,2,4,6]:
  key=('loaded',w,read,262144,64);v=g[key];b=bw[key];tab.append([read,w,round(b[0],3),round(v[0],2)]);ps.append((b[0],*v))
 series.append((f'{read}% reads',ps))
plot(P/'figures/loaded.svg','Memory throughput versus probe latency','Useful background GB/s','Probe latency (ns)',series,notes='Separate probe population; worker completion may extend beyond probe interval. See methodology.')
pages=[]
for n in [256,1024,4096,16384,65536]:pages.append([n,round(g['pages',0,100,n,64][0],2),round(g['pages',0,100,n,4096][0],2)])
plot(P/'figures/pages.svg','Matched node count: packed versus scattered pages','Nodes (log2)','Dependent-load latency (ns)',[(f'{s} B spacing',[(n,*g['pages',0,100,n,s]) for n in [256,1024,4096,16384,65536]]) for s in [64,4096]],True,'Same touched line count; spacing changes page pressure AND potential cache-set conflicts.')
(P/'EXTENDED-RESULTS.md').write_text('\n'.join(['# Extended memory results','',f'{len(rows)} validated trials; three per condition.','',table(['Read %','Load workers','Useful GB/s','Probe ns/load'],tab),'','## Page locality','',table(['Nodes','64 B spacing ns','4096 B spacing ns'],pages),'','Page spacing alone does not prove TLB misses: cache-set conflicts and allocation footprint also change. Hardware counters are unavailable in this WSL instance.']))
(P/'data/extended-summary.json').write_text(json.dumps([dict(study=k[0],workers=k[1],reads=k[2],nodes=k[3],stride=k[4],latency_ns=v,traffic_GB_s=bw[k]) for k,v in g.items()],indent=2))
P=R/'project-3-ssd'
if not (P/'data/index.jsonl').exists():sys.exit(0)
rows=[]
for idx in load(P/'data/index.jsonl'):
 data=json.loads((P/'data/raw'/(idx['name']+'.json')).read_text());j=data['jobs'][0];r=dict(idx);r['fio_error']=j['error'];r['iodepth_level']=j['iodepth_level'];r['iops']=sum(j[d]['iops'] for d in ['read','write']);r['MB_s']=sum(j[d]['bw_bytes'] for d in ['read','write'])/1e6
 total=sum(j[d]['total_ios'] for d in ['read','write']);r['mean_lat_us']=sum(j[d]['lat_ns']['mean']*j[d]['total_ios'] for d in ['read','write'])/total/1000
 for d in ['read','write']:
  r[d+'_ios']=j[d]['total_ios']
  for pct in ['50.000000','95.000000','99.000000','99.900000']:r[d+'_p'+pct.split('.')[0]+('_9' if pct=='99.900000' else '')+'_us']=j[d].get('lat_ns',{}).get('percentile',{}).get(pct,0)/1000
 r['estimated_outstanding']=r['iops']*r['mean_lat_us']*1e-6;rows.append(r)
(P/'data/processed.json').write_text(json.dumps(rows,indent=2))
baseline=[]
for rw in ['randread','randwrite','read','write']:
 rs=[r for r in rows if r['study']=='baseline' and r['rw']==rw];d='read' if 'read' in rw else 'write'
 if rs:baseline.append([rw,rs[0]['bs_kib'],*[round(statistics.median(r[k] for r in rs),2) for k in ['iops','MB_s','mean_lat_us',d+'_p50_us',d+'_p95_us',d+'_p99_us',d+'_p99_9_us']]])
curve=[];ps=[]
for qd in [1,2,4,8,16,32,64,128,256]:
 rs=[r for r in rows if r['study']=='queue' and r['qd']==qd]
 if not rs:continue
 lat=stats([r['mean_lat_us'] for r in rs]);io=stats([r['iops'] for r in rs]);curve.append([qd,round(io[0]),round(lat[0],2),round(statistics.median(r['read_p99_us'] for r in rs),2),round(statistics.median(r['read_p99_9_us'] for r in rs),2),round(statistics.median(r['estimated_outstanding'] for r in rs),2)]);ps.append((io[0],*lat))
if ps:plot(P/'figures/queue.svg','SSD 4 KiB random read: throughput and latency','IOPS','Mean total I/O latency (us)',[('Increasing QD',ps)],notes='Same-run throughput and total latency. Queue-depth rows and achieved-depth distributions retained.')
mix=[]
for pct in [0,50,70,100]:
 rs=[r for r in rows if r['study']=='mix' and r['read_percent']==pct]
 if rs:mix.append([pct,*[round(statistics.median(r[k] for r in rs),2) for k in ['iops','MB_s','mean_lat_us']]])
blocks=[]
for rw in ['read','write','randread','randwrite']:
 series=[]
 for bs in [4,16,32,64,128,256]:
  rs=[r for r in rows if r['study']=='block' and r['rw']==rw and r['bs_kib']==bs]
  if rs:
   b=stats([r['MB_s'] for r in rs]);series.append((bs,*b));blocks.append([rw,bs,round(b[0],2),round(statistics.median(r['mean_lat_us'] for r in rs),2)])
 if series:plot(P/f'figures/{rw}-blocks.svg',f'SSD {rw}: block-size sweep','Block size (KiB, log2)','MB/s',[(rw,series)],True)
knee=min((r[0] for r in curve if r[1]>=.9*max(x[1] for x in curve)),default=None)
extra=[]
for study in ['range','pitfall']:
 for size in [64,2048]:
  for direct in [0,1]:
   rs=[r for r in rows if r['study']==study and r['range_mib']==size and r['direct']==direct]
   if rs:extra.append([study,size,direct,round(statistics.median(r['iops'] for r in rs)),round(statistics.median(r['mean_lat_us'] for r in rs),2)])
tails=[]
for qd in [8,knee]:
 rs=[r for r in rows if r['study']=='queue' and r['qd']==qd]
 if rs:tails.append([qd,*[round(statistics.median(r[k] for r in rs),2) for k in ['read_p50_us','read_p95_us','read_p99_us','read_p99_9_us']]])
depth=[]
for qd in [1,8,32,64,128,256]:
 rs=[r for r in rows if r['study']=='queue' and r['qd']==qd]
 if rs:
  keys=rs[0]['iodepth_level'];depth.append([qd,', '.join(f'{k}: {statistics.median(r["iodepth_level"][k] for r in rs):.1f}%' for k in keys)])
(P/'RESULTS.md').write_text('\n'.join(['# SSD measured results','',f'{len(rows)} trials. Three-second measurement windows after one-second ramp; short-run results, not steady-state certification.','', '## QD=1 baselines','',table(['Pattern','KiB','IOPS','MB/s','Mean us','p50 us','p95 us','p99 us','p99.9 us'],baseline),'','## Queue depth and tails','',table(['QD','IOPS','Mean us','p99 us','p99.9 us','IOPS * mean seconds'],curve),'',f'Operational knee: first tested QD reaching 90% of maximum observed median IOPS = {knee}. This is a sampled range criterion, not proof of device saturation.','',table(['QD','p50 us','p95 us','p99 us','p99.9 us'],tails),'','## Achieved depth: median percentage per fio depth bucket','',table(['Requested QD','Distribution'],depth),'', '## Read/write mixes: random 4 KiB, QD8','',table(['Read %','IOPS','MB/s','Mean us'],mix),'','## Block size: QD8','',table(['Pattern','KiB','MB/s','Mean us'],blocks),'','## File range and buffered-I/O pitfall','',table(['Study','Range MiB','Direct','IOPS','Mean us'],extra)]))
print('All available data summarized.')
