"""Report for the SSD extension: block size, R/W mix, data pattern, buffering and sustained-write device state.

python common/analyze-ssd-extension.py SESSION   (standard library only; reads retained fio JSON and logs)
"""
import collections,json,pathlib,statistics,sys
from charts import plot
R=pathlib.Path(__file__).resolve().parents[1];S=R/'sessions'/sys.argv[1];X=S/'ssd-extension';F=S/'figures'
env=json.loads((X/'environment.json').read_text());assert env.get('test_files_removed'),'collection incomplete'
index=[json.loads(l) for l in (X/'index.jsonl').read_text().splitlines()]
def job(name):
 d=json.loads((X/'raw'/(name+'.json')).read_text());j=d['jobs'][0];assert j['error']==0;return j
def parse(j):
 dirs=[d for d in ['read','write'] if j[d]['total_ios']>0];ios=sum(j[d]['total_ios'] for d in dirs)
 r={'iops':sum(j[d]['iops'] for d in dirs),'MB_s':sum(j[d]['bw_bytes'] for d in dirs)/1e6,'lat_us':sum(j[d]['total_ios']*j[d]['lat_ns']['mean'] for d in dirs)/ios/1e3}
 for d in dirs:
  r[d+'_lat_us']=j[d]['lat_ns']['mean']/1e3
  for p in ['50.000000','95.000000','99.000000','99.900000']:r[f'{d}_p{p.split(".")[0] if p!="99.900000" else "99.9"}']=j[d]['lat_ns']['percentile'][p]/1e3
 r['p99']=max(r.get(d+'_p99',0) for d in dirs);r['L']=r['iops']*r['lat_us']*1e-6;return r
def readlog(path):
 out=[]
 for line in path.read_text().splitlines():
  f=[x.strip() for x in line.split(',')]
  if len(f)>=2 and f[0].isdigit():out.append((int(f[0])/1000,int(f[1])))
 return out
bw=readlog(next((X/'logs').glob('sustained_bw*.log')));lat=readlog(next((X/'logs').glob('sustained_lat*.log')))
mbs=[(t,v*1024/1e6) for t,v in bw]  # fio bandwidth logs are KiB/s
# The sustained trace alternates between two states; split at the midpoint of its range.
split=(max(v for _,v in mbs)+min(v for _,v in mbs))/2;high=[v for _,v in mbs if v>=split];low=[v for _,v in mbs if v<split]
slc_rate,tlc_rate=statistics.median(high),statistics.median(low)
def thermal_section():
 """Temperature logged every ~2 s (Administrator run of collect-ssd-thermal.ps1) against 1 s write throughput."""
 T=S/'ssd-thermal'
 if not (T/'temperature.csv').exists():return []
 import csv
 te=json.loads((T/'environment.json').read_text(encoding='utf-8-sig'));assert te.get('test_file_removed')
 with (T/'temperature.csv').open(encoding='utf-8-sig') as f:temps=[(float(r['t']),int(r['temperature_c']),r['phase']) for r in csv.DictReader(f)]
 w0=te['write_start_s'];tbw=[(t,v*1024/1e6) for t,v in readlog(T/'logs'/'thermal_bw.1.log')]
 def temp_at(t):return min(temps,key=lambda s:abs(s[0]-(t+w0)))[1]  # nearest sample on the write-time axis
 tsplit=(max(v for _,v in tbw)+min(v for _,v in tbw))/2;fast=[(t,v) for t,v in tbw if v>=tsplit];slow=[(t,v) for t,v in tbw if v<tsplit]
 first_slow=min(t for t,_ in slow);first_gib=sum(v for t,v in fast if t<first_slow)*1e6/2**30
 hot=max(temp_at(t) for t,_ in tbw);hot_rate=statistics.median(v for t,v in tbw if temp_at(t)==hot)
 xs=[v for _,v in tbw];ys=[temp_at(t) for t,_ in tbw];mx,my=statistics.mean(xs),statistics.mean(ys)
 corr=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))**.5
 idle=[c for t,c,ph in temps if ph=='idle-before'];after=[c for t,c,ph in temps if ph=='idle-after']
 wj=parse(json.loads((T/'raw'/'thermal-write.json').read_text())['jobs'][0])
 plot(F/'ssd-thermal-temp.svg','SSD temperature: idle, 30 GiB write, recovery','Seconds since start','Drive temperature (C)',[(ph,[(t,c,c,c) for t,c,p in temps if p==ph]) for ph in ['idle-before','write','idle-after']],notes='Windows storage reliability counter (Administrator), sampled about every 2 s.',subtitle='Measured Windows results | single run')
 plot(F/'ssd-thermal-bw.svg','Same run: 1 s write throughput','Seconds since write start','MB/s',[('128 KiB sequential write, QD32',[(t,v,v,v) for t,v in tbw])],notes=f'Write started {w0:.0f} s after the temperature log.',subtitle='Measured Windows results | single run, 1 s averages')
 return ['## Temperature: is the slowdown thermal?','',
 f'A separate Administrator run of [`collect-ssd-thermal.ps1`](../../common/collect-ssd-thermal.ps1) logged the drive temperature about every 2 s through 60 s idle, a {te["size_gib"]} GiB 128 KiB sequential write at QD32 ({wj["MB_s"]:.0f} MB/s average), and 180 s of recovery. [Prediction](ssd-thermal/HYPOTHESES.md), [samples](ssd-thermal/temperature.csv), [run log](ssd-thermal/run-log.txt).','',
 '![Temperature](figures/ssd-thermal-temp.svg)','![Throughput in the same run](figures/ssd-thermal-bw.svg)','',
 f'Temperature rose from {statistics.median(idle):.0f} C at idle to a peak of {hot} C during the write and settled at {min(after)}-{max(after)} C afterwards. Throughput again alternated between about {statistics.median(v for _,v in fast):.0f} MB/s and {statistics.median(v for _,v in slow):.0f} MB/s, but **the drive was writing at {hot_rate:.0f} MB/s while it was hottest**, and the slow phase occurred at lower temperatures than the fast phase that followed it. The correlation between 1 s throughput and temperature is {corr:+.2f}. Thermal throttling would make the hottest seconds the slowest, so it is excluded at these temperatures. The slow phases are SLC-cache exhaustion, as predicted.','',
 f'**Cache size depends on device state.** On this rested drive the first fast phase wrote {first_gib:.1f} GiB before slowing; in the sustained run that followed the write-heavy matrix, fast phases wrote about 2 GiB each. The SLC cache is dynamic: its usable size depends on free space and on how much of it the controller has already folded into TLC. A "cache size" measured once is not a property of the drive alone.','',
 'Small temperature bumps during the recovery period, with no host I/O from this test, may be background folding by the controller; this is not established.','']
rows=[]
for i in index:r=dict(i);r.update(parse(job(i['name'])));rows.append(r)
(X/'processed.json').write_text(json.dumps(rows,indent=1))
G=collections.defaultdict(list)
for r in rows:G[r['study'],r['rw'],r['bs_kib'],r['read_percent'],r['compress_percent'],r['direct']].append(r)
def m(key,f):v=[f(r) for r in G[key]];return statistics.median(v),min(v),max(v)
iv=lambda v,p=1:f'{v[0]:.{p}f} [{v[1]:.{p}f}, {v[2]:.{p}f}]'
BS=[4,16,32,64,128,256];RW=[('randread',100),('read',100),('randwrite',0),('write',0)]
L=['# SSD extension: block size, mix, data pattern, buffering and device state','',
f'Same host and drive as the Ryzen QD study (**ADATA SU650**, SATA 6 Gb/s, NTFS system volume, 16 GiB RAM), fio {env["fio"].replace("fio-","")}, `windowsaio`, one job. Disposable files only: a 2 GiB prefilled and CRC32C-verified matrix file and a {env["sustained_bytes"]//2**30} GiB sustained-write file, both deleted after success. Matrix runs: 5 s after a 2 s ramp, 3 trials per condition, all {len(rows)} runs interleaved in one shuffled order. [Predictions](ssd-extension/HYPOTHESES.md) were written before collection; [configs](ssd-extension/configs/), [raw JSON](ssd-extension/raw/), [1 s logs](ssd-extension/logs/).','',
'Fixed unless stated: direct I/O, QD32 (the SATA NCQ limit, so every request can be outstanding in the drive), incompressible buffers, 2 GiB LBA range. Throughput and latency in each row come from the same runs.','',
'## Block-size sweep (QD32)','',
'| Pattern | Block KiB | IOPS [min,max] | MB/s [min,max] | Mean latency us | p99 us | Little L = IOPS x latency |','|---|---:|---|---|---:|---:|---:|']
for rw,rp in RW:
 for bs in BS:
  k=('blocksize',rw,bs,rp,0,1);L.append(f'| {rw} | {bs} | {iv(m(k,lambda r:r["iops"]),0)} | {iv(m(k,lambda r:r["MB_s"]))} | {m(k,lambda r:r["lat_us"])[0]:.0f} | {m(k,lambda r:r["p99"])[0]:.0f} | {m(k,lambda r:r["L"])[0]:.1f} |')
plot(F/'ssd-ext-blocksize.svg','SATA SSD throughput versus block size (QD32)','Block size KiB (log2)','MB/s',[(rw,[(bs,*m(('blocksize',rw,bs,rp,0,1),lambda r:r['MB_s'])) for bs in BS]) for rw,rp in RW],True,'Direct I/O, 2 GiB file, 3 trials; SATA 6 Gb/s carries at most about 600 MB/s before protocol overhead.')
plot(F/'ssd-ext-blocksize-lat.svg','Mean latency versus block size (QD32)','Block size KiB (log2)','Mean total latency (us)',[(rw,[(bs,*m(('blocksize',rw,bs,rp,0,1),lambda r:r['lat_us'])) for bs in BS]) for rw,rp in RW],True,'Same runs as the throughput figure.')
rr=lambda rw,bs,f='MB_s':m(('blocksize',rw,bs,100 if 'read' in rw else 0,0,1),lambda r:r[f])[0]
L+=['','![Block size](figures/ssd-ext-blocksize.svg)','![Block-size latency](figures/ssd-ext-blocksize-lat.svg)','',
f'**Interpretation.** Small requests are IOPS-limited ({rr("randread",4,"iops"):,.0f} random-read IOPS at 4 KiB, only {rr("randread",4):.0f} MB/s). From 16 KiB upward reads reach roughly 400-540 MB/s, the practical SATA 6 Gb/s ceiling, and random and sequential reads are within each other\'s trial ranges: once a request spans several flash pages, the drive\'s die parallelism hides the cost of a random address. Once bandwidth-bound, latency grows with transfer size: at a fixed queue, Little\'s Law gives latency = L / IOPS.','',
f'**Requested versus achieved queue depth (pitfall).** L = IOPS x mean latency is 31.5-32 in most rows, so 32 requests really were outstanding. Two rows are not: 4 KiB random write (L = {rr("randwrite",4,"L"):.1f}) and 4 KiB sequential read (L = {rr("read",4,"L"):.1f}). Those requests complete so fast that a single fio thread cannot resubmit quickly enough, so the effective depth is lower than the configured `iodepth=32`. Reporting those rows as "QD32" would be the misleading-setup error the assignment describes.','',
f'**Bimodal writes (device state inside the matrix).** Many write rows have a minimum of about 75-80 MB/s while their medians are 370-470 MB/s. That low value matches the post-cache rate in the sustained test below (about {tlc_rate:.0f} MB/s). Because write runs were interleaved, a run that followed other writes sometimes found the SLC cache full. Write medians are therefore burst numbers, and write p99 values of 30-100 ms are the stalls of those cache-full runs.','']
# ---- mix ----
L+=['## Read/write mix (4 KiB random, QD32)','','| Read % | Total IOPS [min,max] | MB/s | Read mean / p99 us | Write mean / p99 us |','|---:|---|---:|---|---|']
MIX=[100,70,50,0]
for pct in MIX:
 k=('mix','randrw',4,pct,0,1);rd=f'{m(k,lambda r:r["read_lat_us"])[0]:.0f} / {m(k,lambda r:r["read_p99"])[0]:.0f}' if pct else 'n/a';wr=f'{m(k,lambda r:r["write_lat_us"])[0]:.0f} / {m(k,lambda r:r["write_p99"])[0]:.0f}' if pct<100 else 'n/a'
 L.append(f'| {pct} | {iv(m(k,lambda r:r["iops"]),0)} | {m(k,lambda r:r["MB_s"])[0]:.1f} | {rd} | {wr} |')
plot(F/'ssd-ext-mix.svg','4 KiB random read/write mix (QD32)','Read percentage','Total IOPS',[('Total IOPS',[(p,*m(('mix','randrw',4,p,0,1),lambda r:r['iops'])) for p in sorted(MIX)])],notes='3 trials per mix; whiskers min-max.')
mi=lambda p:m(('mix','randrw',4,p,0,1),lambda r:r['iops'])[0]
L+=['','![Mix](figures/ssd-ext-mix.svg)','',
f'**Interpretation.** Pure reads give {mi(100):,.0f} IOPS and pure writes {mi(0):,.0f}. The 70/30 mix ({mi(70):,.0f}) lies between them'+(f', but the 50/50 mix ({mi(50):,.0f}) falls below both pure cases.' if mi(50)<min(mi(100),mi(0)) else f' and so does the 50/50 mix ({mi(50):,.0f}).')+' The latency columns show why: in mixed traffic, *read* latency rises well above the pure-read value while writes, acknowledged once they reach the SLC cache, stay fast. Reads queue behind NAND program operations on the same dies. Short 4 KiB writes are absorbed by the SLC cache here, so this is burst behavior, not steady state.','']
# ---- data pattern ----
L+=['## Data pattern (128 KiB sequential write, QD32)','','| Buffer compressibility | MB/s [min,max] | Mean latency us | p99 us |','|---:|---|---:|---:|']
for c in [0,50,90]:
 k=('pattern','write',128,0,c,1);L.append(f'| {c}% | {iv(m(k,lambda r:r["MB_s"]))} | {m(k,lambda r:r["lat_us"])[0]:.0f} | {m(k,lambda r:r["p99"])[0]:.0f} |')
pc=[m(('pattern','write',128,0,c,1),lambda r:r['MB_s'])[0] for c in [0,50,90]]
rng=[m(('pattern','write',128,0,c,1),lambda r:r['MB_s']) for c in [0,50,90]]
L+=['',f'**Interpretation.** Medians differ by up to {100*(max(pc)/min(pc)-1):.0f}%, but the trial ranges overlap ({", ".join(f"{lo:.0f}-{hi:.0f}" for _,lo,hi in rng)} MB/s), and the low ends sit at the SLC-cache-full write rate. Device state, not data content, decides each run, and the most compressible data is not the fastest. There is no evidence that this controller compresses data, so "compressible data is faster" does not help here. Buffers are held incompressible everywhere else so that results would not be inflated on a drive that does compress.','']
# ---- buffering ----
L+=['## Misleading setup: buffered versus direct I/O (4 KiB random read, QD1)','','| Mode | IOPS [min,max] | Mean us | p50 us | p99 us |','|---|---|---:|---:|---:|']
for d,name in [(0,'buffered (OS page cache allowed)'),(1,'direct (cache bypassed)')]:
 k=('buffering','randread',4,100,0,d);L.append(f'| {name} | {iv(m(k,lambda r:r["iops"]),0)} | {m(k,lambda r:r["lat_us"])[0]:.1f} | {m(k,lambda r:r["read_p50"])[0]:.1f} | {m(k,lambda r:r["read_p99"])[0]:.1f} |')
b0,b1=[m(('buffering','randread',4,100,0,d),lambda r:r['iops'])[0] for d in [0,1]]
warm=[json.loads(l) for l in (X/'warm-index.jsonl').read_text().splitlines()] if (X/'warm-index.jsonl').exists() else []
if warm:
 wr=[parse(job(w['name'])) for w in warm];wi=statistics.median(r['iops'] for r in wr)
 L.append(f'| buffered, cache pre-warmed by a full read | {iv((wi,min(r["iops"] for r in wr),max(r["iops"] for r in wr)),0)} | {statistics.median(r["lat_us"] for r in wr):.1f} | {statistics.median(r["read_p50"] for r in wr):.1f} | {statistics.median(r["read_p99"] for r in wr):.1f} |')
L+=['',f'**Interpretation (prediction wrong in an instructive way).** The cold buffered run is *slower*, {b0/b1:.2f}x the direct IOPS. The file was written with direct I/O, so it was not in the page cache, and 5 s of random 4 KiB reads touch only a small fraction of 2 GiB: almost every read still goes to the SSD, now with the Windows cache manager\'s mapping and copy overhead added. Buffered I/O can therefore make the drive look slower than it is.'+(f' After the whole file is first read sequentially, buffered random reads reach {wi:,.0f} IOPS, {wi/b1:.0f}x the direct result: the benchmark is now measuring RAM, not the SSD. The same `direct=0` setting can understate or overstate the device depending on cache state, which is why every other run uses direct I/O.' if warm else ' The opposite error, inflated results from a warm page cache, needs a pre-read file and was demonstrated on the Intel laptop.'),'']
# ---- sustained ----
# Episodes: maximal runs of consecutive seconds in the same (fast/slow) state.
eps=[];cur=None
for t,v in mbs:
 st=v>=split
 if cur and cur[0]==st:cur[2]=t;cur[3]+=v
 else:
  cur=[st,t,t,v];eps.append(cur)
fast=[e for e in eps if e[0] and e[2]-e[1]>=2];slow=[e for e in eps if not e[0] and e[2]-e[1]>=2]
fast_gib=statistics.median(e[3]*1e6/2**30 for e in fast) if fast else 0
slow_frac=len(low)/len(mbs)
sj=parse(job('sustained-write'));pj=parse(job('post-sustained-burst'));ij=parse(job('after-idle-burst'))
latms=[(t,v/1e3) for t,v in lat]  # fio latency logs are ns
plot(F/'ssd-ext-sustained.svg','Sustained 128 KiB sequential write (QD32): 1 s throughput','Elapsed seconds','MB/s',[('Write throughput',[(t,v,v,v) for t,v in mbs])],notes='One run; 1 s averages from fio write_bw_log. Fast plateaus = SLC cache; slow plateaus = direct TLC writes while folding.',subtitle='Measured Windows results | single sustained run, 1 s averages')
plot(F/'ssd-ext-sustained-lat.svg','Sustained write: 1 s mean completion latency','Elapsed seconds','Mean latency (us)',[('Write latency',[(t,v,v,v) for t,v in latms])],notes='Same run; fio write_lat_log averaged over 1 s windows.',subtitle='Measured Windows results | single sustained run, 1 s averages')
dur=json.loads((X/'raw'/'sustained-write.json').read_text())['jobs'][0]['write']['runtime']/1e3
total_gib=json.loads((X/'raw'/'sustained-write.json').read_text())['jobs'][0]['write']['io_bytes']/2**30
L+=['## Device state: burst versus sustained writes','',
f'One sequential 128 KiB write at QD32 to a new {env["sustained_bytes"]//2**30} GiB file, logged every second, then a 20 s burst immediately after, then 120 s idle and another 20 s burst. It wrote {total_gib:.1f} GiB in {dur:.0f} s (average {sj["MB_s"]:.0f} MB/s).','',
'![Sustained write](figures/ssd-ext-sustained.svg)','![Sustained latency](figures/ssd-ext-sustained-lat.svg)','',
f'**The trace is a sawtooth, not a single cliff.** Throughput alternates between two plateaus: about **{slc_rate:.0f} MB/s** ({len(fast)} fast episodes, each writing a median {fast_gib:.1f} GiB) and about **{tlc_rate:.0f} MB/s** ({len(slow)} slow episodes). The drive spent {100*slow_frac:.0f}% of the seconds in the slow state. This is how a DRAM-less TLC drive with a small, dynamic SLC cache behaves: writes go to a few GiB of fast single-bit-per-cell blocks; when those fill, new writes go to TLC at about {tlc_rate:.0f} MB/s while the controller folds SLC data into TLC and frees cache, and when enough is freed, fast writes resume. The first cache-full drop came after only about 12 s because the preceding matrix had just written to the drive. Mean latency mirrors throughput: at a fixed QD32, Little\'s Law ties latency to 32/IOPS, so the slow state has about {slc_rate/tlc_rate:.0f}x the latency.','',
f'**Prediction check:** a cliff was predicted. The measured repeating sawtooth shows a single "steady-state write speed" is not a meaningful number for this drive. The long-run average ({sj["MB_s"]:.0f} MB/s) is a blend that depends on how long the workload runs and how much idle time the controller gets.','',
'| Phase | MB/s | Mean us | p99 us | p99.9 us |','|---|---:|---:|---:|---:|',
*[f'| {n} | {j["MB_s"]:.0f} | {j["lat_us"]:.0f} | {j["write_p99"]:.0f} | {j["write_p99.9"]:.0f} |' for n,j in [('Whole sustained run',sj),('20 s burst right after',pj),('20 s burst after 120 s idle',ij)]],'',
f'**Recovery:** after 120 s idle the burst runs at {ij["MB_s"]:.0f} MB/s versus {pj["MB_s"]:.0f} MB/s immediately after the sustained write. '+('Idle time let the controller migrate SLC contents to TLC and free cache space, so short tests on a rested drive see burst speeds that a long workload does not.' if ij['MB_s']>1.2*pj['MB_s'] else 'Two minutes of idle time did not restore burst speed in this run; background folding may need longer, or the burst file region (2 GiB, overwritten) is handled differently from new data.'),'',
f'**Why this matters for the other results:** every matrix run wrote at most a few GiB with idle gaps, so all write numbers above and in the QD study are burst (SLC-cache) numbers, not steady state. Temperature could not be read during this (non-elevated) collection (`smart_before` in [environment.json](ssd-extension/environment.json) retains the refusal); a separate Administrator run below logs it and rules out thermal throttling.','',
*thermal_section(),
'## Limits','','- Three 5 s trials per matrix condition; one sustained run. Ranges are min/max, not confidence intervals.','- 2 GiB LBA range on a partly used system drive; the full-drive random-write steady state (after preconditioning the whole device) was not measured, to avoid filling the system volume.','- QD32 is the SATA NCQ limit; deeper host queues only add waiting time in Windows (see the QD study).']
(S/'SSD-EXTENSION.md').write_text('\n'.join(L)+'\n',encoding='utf-8');print('SSD extension report written',len(rows))
