"""Rebuild the named follow-up report/figures from retained raw data (no measurements)."""
import collections,json,pathlib,statistics,sys,re
from charts import plot
R=pathlib.Path(__file__).resolve().parents[1];P=R/'sessions'/sys.argv[1];F=P/'figures';F.mkdir(exist_ok=True)
def load(name):return [json.loads(x) for x in (P/name).read_text().splitlines()]
def stat(v):return statistics.median(v),min(v),max(v)
def grouped(rows,keys,metric):
 d=collections.defaultdict(list)
 for r in rows:d[tuple(r[k] for k in keys)].append(r[metric])
 return {k:stat(v) for k,v in d.items()}
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(v) for v in row)+' |' for row in rows])
def fmt(v):return f'{v:.3f}'
def interval(v):return f'{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]'
env=json.loads((P/'environment.json').read_text());simd=load('simd.jsonl');lat=load('latency.jsonl');band=load('bandwidth.jsonl')
g=grouped(simd,['dtype','build','kind','n','stride','offset_elements'],'ns_element');through=grouped(simd,['dtype','build','kind','n','stride','offset_elements'],'gflops')
sizes=sorted({r['n'] for r in simd if r['kind']==2});names=['AXPY','Multiply','Ordered dot']
caches=[(c['bytes']/1024,f'L{c["level"]}') for c in env['topology']['cores'][0]['caches'] if c['type'] in [1,3]]
lines=['# October follow-up: SIMD, memory and SSD','',f'Host: **{env["cpu"].strip()}**, {env["os"]}; {env["compiler"].splitlines()[0]}. This is a separate machine/session from the retained Intel laptop studies. Do not pool their trials.','',
'## Method and evidence status','',
'Five repetitions per timed condition; fixed shuffled ordering within each suite. CPU tests use affinity to CPU0, warm-up, deterministic initialization and reference checks. Balanced policy remains active; frequency is not locked, SMT is enabled, and cores are not exclusively reserved. Normal desktop activity and assistant editing/tool calls continued. Min/max bars show observed variation, not confidence intervals. [Environment and topology](environment.json), [build commands](builds.json), [pre-experiment predictions](HYPOTHESES.md), and [source snapshots](sources/) are retained.','',
'The SIMD suite uses 150 ms minimum windows, a 300 ms streaming reference, and 200 ms dependent-chain windows. The load follow-up uses one-second windows. The SSD follow-up uses five seconds after a two-second ramp. These are bounded observations rather than a steady-state certification.','',
'## Project 1: SIMD','',
'The three kernels, strict summation order and FMA-disabled build flags match the original study. AXPY is explicitly out of place (`z = 1.25*x + y`), so its footprint differs from in-place AXPY. Binary-fraction inputs allow checks against a scalar double reference. Each row retains its measured error and tolerance. Useful GB/s counts two reads plus one write (dot: two reads); it is not measured bus traffic.','']
findings=[]
for dtype in ['float','double']:
 for kind in range(3):
  series=[]
  for b in ['auto','native']:
   points=[]
   for n in sizes:
    base=g[dtype,'scalar',kind,n,1,0];v=g[dtype,b,kind,n,1,0];points.append((n,base[0]/v[0],base[1]/v[2],base[2]/v[1]))
   series.append((b,points))
  plot(F/f'{dtype}-{kind}-speedup.svg',f'{dtype} {names[kind]} speedup','Elements N (log2)','Scalar / vectorized time',series,True,'Ratio whiskers use independent extrema; they are not paired confidence intervals.')
  width=4 if dtype=='float' else 8;arrays=2 if kind==2 else 3
  plot(F/f'{dtype}-{kind}-locality.svg',f'{dtype} {names[kind]}: locality','Logical array footprint (KiB, log2)','GFLOP/s',[(b,[(n*width*arrays/1024,*through[dtype,b,kind,n,1,0]) for n in sizes]) for b in ['scalar','auto','native']],True,'Cache markers are capacities, not proof of residency.',caches)
  for n in [1024,16777216]:findings.append([dtype,names[kind],n,fmt(g[dtype,'scalar',kind,n,1,0][0]/g[dtype,'native',kind,n,1,0][0]),interval(through[dtype,'native',kind,n,1,0])])
lines += [table(['Type','Kernel','N','Native speedup','Native GFLOP/s median [min,max]'],findings),'','![SIMD speedup](figures/float-0-speedup.svg)','![Locality](figures/float-0-locality.svg)','',
'### Alignment, tails and stride','',
'Tables keep the four aligned/shifted and divisible/remainder cases separate. Small loops include timer/call overhead; differences of a few nanoseconds cannot be assigned wholly to vector prologue or tail code. A one-element offset misaligns the base by four/eight bytes; compiler evidence determines the actual vector width. Larger stride expands the span and reduces useful bytes per cache line.','']
alignment=[];stride=[]
for dtype in ['float','double']:
 for n in [16,19,65536,65539]:
  for off in [0,1]:alignment.append([dtype,n,off,*[interval(g[dtype,b,0,n,1,off]) for b in ['scalar','auto','native']]])
 for s in [1,2,4,8]:stride.append([dtype,s,*[interval(g[dtype,b,1,524288,s,0]) for b in ['scalar','auto','native']]])
 plot(F/f'{dtype}-stride.svg',f'{dtype} multiply: stride study','Element stride','ns / useful element',[(b,[(s,*g[dtype,b,1,524288,s,0]) for s in [1,2,4,8]]) for b in ['scalar','auto','native']],notes='N=524288; stride changes span and useful cache-line utilization.')
lines += [table(['Type','N','Offset','Scalar ns/element','Auto ns/element','Native ns/element'],alignment),'',table(['Type','Stride','Scalar ns/element','Auto ns/element','Native ns/element'],stride),'','![Stride](figures/float-stride.svg)','']
for dtype in ['float','double']:
 aligned=g[dtype,'native',0,65536,1,0][0];shift=g[dtype,'native',0,65536,1,1][0];tail=g[dtype,'native',0,65539,1,0][0]
 lines += [f'{dtype}: shifting N=65536 by one element changes median native time/element by {100*(shift/aligned-1):+.1f}%; adding a three-element tail changes it by {100*(tail/aligned-1):+.1f}%. These are observed differences, not isolated instruction latencies.']
lines += ['',f'At N=1024, native float32 AXPY throughput is {through["float","native",0,1024,1,0][0]/through["double","native",0,1024,1,0][0]:.2f}x float64 throughput; at N=16777216 it is {through["float","native",0,16777216,1,0][0]/through["double","native",0,16777216,1,0][0]:.2f}x. Float32 packs twice as many lanes and has twice the useful arithmetic intensity. Overhead and memory limits prevent a universal exact 2x rule.','',
'### Vector evidence and negative case','']
evidence=(P/'evidence/float-native-vector.txt').read_text().splitlines()
snippets=[x.split('simd.c:')[-1] for x in evidence if 'optimized:' in x and any('simd.c:'+str(i)+':' in x for i in [16,17,18])][:8]
assembly=(P/'evidence/float-native-assembly.txt').read_text();kernel=assembly.split('<kernel>:',1)[1].split('\n\n',1)[0]
instructions=[x.strip() for x in kernel.splitlines() if re.search(r'\b(vmulps|vaddps|vaddss)\b',x)]
lines += ['Native compiler excerpts (source line, diagnostic):','','```text',*snippets,'```','','Selected instructions from this session\'s `kernel` function:','','```text',*instructions[:2],*instructions[6:10],'```','',
'The report shows 32-byte main vectors and narrower epilogues. That means eight float32 or four float64 lanes, not a promised 8x/4x speedup. FMA contraction remains off. The ordered reduction preserves serial addition dependencies even when products vectorize. Full disassembly is retained under `evidence/`; the original targeted [instruction explanation](../../project-1-simd/VECTOR-EVIDENCE.md) applies to the original compiler, not automatically to this new build.','']
neg=[(d,k,n,g[d,'scalar',k,n,1,0][0]/g[d,'native',k,n,1,0][0]) for d in ['float','double'] for k in range(3) for n in sizes]
negative=min(neg,key=lambda x:x[3]);lines += [f'The smallest measured native/scalar speedup is **{negative[3]:.3f}x** for {negative[0]} {names[negative[1]]}, N={negative[2]}. It is retained even though the native target is intended as an optimization. Compare its variation and assembly before attributing the loss solely to vector width.','',
'### Roofline with a traffic-matched reference','',
'The independent streaming reference performs `z=x+y` using aligned AVX2 loads and ordinary cached stores, with the same two-read/one-write pattern and FP32 array sizes as AXPY. It validates every result before and after timing. It remains an empirical useful-bandwidth reference rather than a hardware upper limit. At the useful-byte level AXPY has 2/12=1/6 FLOP/B and multiply 1/12 FLOP/B; dot is 2/8=1/4 but has a different traffic mix.','']
b=grouped(band,['n'],'useful_GB_s');bt=[]
for n in [4194304,16777216]:bt.append([n,interval(b[n,]),fmt(b[n,][0]/6),fmt(through['float','native',0,n,1,0][0]),fmt(through['float','native',0,n,1,0][0]/(b[n,][0]/6))])
lines += [table(['N','Reference GB/s [min,max]','AXPY reference GFLOP/s','Observed AXPY GFLOP/s','Observed / reference'],bt),'',
'For a physical-traffic model with write allocation, 16 rather than 12 bytes/element gives 1/8 FLOP/B for AXPY. A measured **useful** GB/s number cannot be multiplied by that physical intensity without also changing its byte convention. Doing so was a limitation of the earlier read-only proxy. These new tables use one consistent useful-byte convention; without controller counters, physical traffic is still unmeasured.','',
'A compute sensitivity line can be estimated as vector operations/cycle × lanes × FLOPs/operation × GHz. For example, an explicitly assumed two 256-bit vector operations/cycle gives 16 FP32 FLOPs/cycle for separate add/multiply, or 32 for two FMAs. At assumed 2/3/4 GHz the separate-operation scenarios are 32/48/64 GFLOP/s. These are scenario ceilings, not measured clock rates or a claim that each kernel can saturate every execution unit. The actual compiled code disables FMA. Low intensity and falling SIMD gains support a data-movement explanation; a reference exceedance must remain visible.','']
B=b[16777216,][0];xs=[.01,.025,.05,1/12,1/6,.25,.5,1,2,4,8,16]
plot(F/'roofline.svg','Empirical FP32 roofline sensitivity','Useful arithmetic intensity (FLOP/byte, log2)','GFLOP/s',[(f'{GHz} GHz scenario',[(x,min(16*GHz,B*x),min(16*GHz,B*x),min(16*GHz,B*x)) for x in xs]) for GHz in [2,3,4]],True,'Two-read/one-write reference; empirical envelope, not verified bus or CPU peak.',subtitle='Measured bandwidth slope; illustrative compute ceilings (no measured clock claim)')
lines += ['![Empirical roofline](figures/roofline.svg)','',
'## Project 2: memory hierarchy','',
'The dependent random chain serializes demand loads, and the predictable chain is a controlled misleading-benchmark example. Every permutation is checked as one cycle, with final index validation after timing. Capacity transitions are expectations based on CPUID, not assigned from convenient latency jumps.','']
lg=grouped(lat,['bytes','pattern'],'ns_per_op');foot=sorted({r['bytes'] for r in lat})
plot(F/'latency.svg','Ryzen cache and memory footprint sweep','Allocated/touched-line footprint (KiB, log2)','ns / dependent load',[(pat,[(n/1024,*lg[n,pat]) for n in foot]) for pat in ['random','sequential']],True,'64 B spacing: one selected pointer per cache line; ordinary pages.',caches)
plot(F/'latency-cache-zoom.svg','L1/L2 transition detail','Touched-line footprint (KiB, log2)','ns / dependent load',[(pat,[(n/1024,*lg[n,pat]) for n in foot if n<=1048576]) for pat in ['random','sequential']],True,'Zoom of the same trials; no data removed from the complete sweep.',caches)
lines += ['![Memory hierarchy](figures/latency.svg)','![Cache zoom](figures/latency-cache-zoom.svg)','',table(['Footprint KiB','Random ns/load [min,max]','Sequential ns/load [min,max]'],[[n//1024,interval(lg[n,'random']),interval(lg[n,'sequential'])] for n in foot]),'',
'This denser sweep reduces the risk of skipping a transition. Random-chain latency includes translation and cache effects. Sequential latency can be far smaller because predictability enables prefetching; it is not intrinsic random DRAM latency. Hardware-counter correlation is still required before separating cache and TLB causes. The original [pattern/granularity and R/W matrix](../../project-2-memory/docs/PILOT-README.md) remains a distinct Intel session.','',
table(['Candidate dominant regime','Footprint','Observed random ns/load [min,max]'],[[label,str(n//1024)+' KiB',interval(lg[n,'random'])] for label,n in [('L1',16384),('L2',262144),('LLC',2097152),('DRAM + translation',134217728)]]),'',
'These are low-load candidates, not pure component latencies. The rise around 32 KiB/512 KiB is consistent with reported L1D/L2 capacities. The early, highly variable rise around 4-8 MiB cannot simply be labeled the 16 MiB LLC boundary: competing occupancy, address translation, scheduling, physical mapping and boost state are plausible contributors. The 4 MiB maximum is retained, not discarded as an inconvenient outlier.','']
processed={'simd_groups':len(g),'memory_groups':len(lg),'simd_trials':len(simd),'latency_trials':len(lat),'bandwidth_trials':len(band)}
if (P/'loaded.jsonl').exists():
 rows=load('loaded.jsonl');bg=grouped(rows,['workers','read_percent'],'traffic_GB_s');pg=grouped(rows,['workers','read_percent'],'latency_ns');workers=sorted({r['workers'] for r in rows if r['workers']});tab=[];curves=[]
 for pct in [0,50,70,100]:
  pts=[]
  for w in workers:
   tab.append([pct,w,interval(bg[w,pct]),interval(pg[w,pct])]);pts.append((bg[w,pct][0],*pg[w,pct]))
  curves.append((f'{pct}% reads',pts))
 plot(F/'loaded.svg','Homogeneous-core throughput and latency','Useful background GB/s','Probe latency (ns)',curves,notes='Points ordered by workers 1-5; separate probe/worker populations.')
 plot(F/'load-throughput.svg','Bandwidth versus physical-core workers','Workers','Useful background GB/s',[(f'{p}% reads',[(w,*bg[w,p]) for w in workers]) for p in [0,50,70,100]])
 lines += ['### Contention and a sampled knee','',
 'The probe uses a 64 MiB random chain on CPU0. Up to five AVX2 traffic workers use 128 MiB each on CPUs 2/4/6/8/10, verified as distinct physical cores. SMT stays enabled, with no deliberate sibling workload. Percentages describe 32-byte read/store operations; cache write allocation means physical bus traffic and ratios differ. All buffer initialization precedes timing. Stop checks occur at 128 KiB chunks.','',
 f'Unloaded probe: **{interval(pg[0,100])} ns/load**. Maximum observed start lag: {max(r["start_lag_us"] for r in rows):.1f} us; maximum end overhang: {max(r["end_overhang_us"] for r in rows):.1f} us. Background throughput uses the probe-start to final-worker-end interval, including those edge effects.','',
 '![Contention](figures/loaded.svg)','![Worker scaling](figures/load-throughput.svg)','',table(['Read %','Workers','GB/s [min,max]','Probe ns [min,max]'],tab),'']
 for pct in [0,50,70,100]:
  peak=max(bg[w,pct][0] for w in workers);k=next(w for w in workers if bg[w,pct][0]>=.9*peak)
  gain=100*(bg[workers[-1],pct][0]/bg[workers[-2],pct][0]-1)
  lines += [f'- {pct}% reads: first 90%-of-observed-maximum point is {k} workers; maximum median {peak:.2f} GB/s. The last worker changes throughput by {gain:+.1f}%. A threshold at the last sampled point does not establish saturation.']
 lines += ['',
 'Little\'s Law applies to one request population: L=lambda*W. The background streamers and dependent probe are different populations, so their values cannot be combined into an exact in-flight request count. Their joint curve shows contention. AMAT requires actual conditional miss rates and incremental penalties; capacity labels or timing differences are not substitutes for those rates.','']
 processed['load_trials']=len(rows)
if (P/'ssd/index.jsonl').exists():
 ss=[]
 for index in load('ssd/index.jsonl'):
  job=json.loads((P/'ssd/raw'/(index['name']+'.json')).read_text())['jobs'][0];assert job['error']==0
  ios=sum(job[d]['total_ios'] for d in ['read','write']);r=dict(index);r.update(iops=sum(job[d]['iops'] for d in ['read','write']),MB_s=sum(job[d]['bw_bytes'] for d in ['read','write'])/1e6,lat_us=sum(job[d]['total_ios']*job[d]['lat_ns']['mean'] for d in ['read','write'])/ios/1000,ios=ios)
  direction='read' if 'read' in index['rw'] else 'write'
  for tag in ['50.000000','95.000000','99.000000','99.900000']:r['p'+tag]=job[direction]['lat_ns']['percentile'][tag]/1000
  r['L']=r['iops']*r['lat_us']*1e-6;ss.append(r)
 (P/'ssd/processed.json').write_text(json.dumps(ss,indent=2))
 queue=[r for r in ss if r['study']=='queue'];qg=grouped(queue,['qd'],'iops');ql=grouped(queue,['qd'],'lat_us');qs=sorted({r['qd'] for r in queue});peak=max(v[0] for v in qg.values());knee=next(q for q in qs if qg[q,][0]>=.9*peak)
 plot(F/'ssd-queue.svg','SATA SSD: throughput versus total I/O latency','IOPS','Mean total latency (us)',[('Increasing QD',[(qg[q,][0],*ql[q,]) for q in qs])],notes='One interleaved session; requested QD listed in report.')
 plot(F/'ssd-qd.svg','SATA SSD: sampled queue-depth knee','Requested queue depth (log2)','IOPS',[('Random read 4 KiB',[(q,*qg[q,]) for q in qs])],True,'Five trials per QD; whiskers are min/max. Operational threshold = 90% observed maximum.')
 lines += ['## Project 3: SSD queueing follow-up','',
 'The new host uses an **ADATA SU650 SATA SSD**, NTFS, and a new 2 GiB disposable file. It is not the old laptop SSD. fio uses `windowsaio`, direct I/O, one job, aligned 4 KiB random reads, and incompressible buffers. A complete file prefill and separate CRC32C verification precede the interleaved study. The exact test file is removed only after successful completion. [Configs](ssd/configs/), [raw fio JSON](ssd/raw/), and [collection settings](ssd/environment.json) are retained.','',
 'The original Intel/laptop block-size, read/write-mix, range and buffering studies remain valid for their own device and are linked in the [original SSD report](../../project-3-ssd/README.md). This follow-up addresses the mixed-session QD curve; it does not merge new and old drive results.','',
 f'Within this one session, the maximum median is **{peak:,.0f} IOPS**; the first QD reaching 90% is **QD{knee}**. This is an operational sampled threshold, not a device specification.','',
 '![SSD QD](figures/ssd-qd.svg)','![SSD queueing](figures/ssd-queue.svg)','',
 table(['QD','IOPS [min,max]','Mean us [min,max]','Median L=IOPS*mean seconds'],[[q,interval(qg[q,]),interval(ql[q,]),fmt(stat([r['L'] for r in queue if r['qd']==q])[0])] for q in qs]),'',
 'Throughput and mean total latency come from the same run and population. L is computed per run before aggregation. It can differ from configured QD because fio sometimes has fewer requests outstanding; achieved-depth histograms remain in the raw JSON. A depth bucket of >=64 cannot distinguish QD64 from QD256 by itself.','',
 '### QD1 baselines and tails','',
 table(['Pattern','KiB','IOPS','MB/s','Mean us','p50 us','p95 us','p99 us','p99.9 us'],[[rw,rs[0]['bs_kib'],*[fmt(stat([r[k] for r in rs])[0]) for k in ['iops','MB_s','lat_us','p50.000000','p95.000000','p99.000000','p99.900000']]] for rw in ['randread','randwrite','read','write'] if (rs:=[r for r in ss if r['study']=='baseline' and r['rw']==rw])]),'',
 table(['QD','p50 us','p95 us','p99 us','p99.9 us'],[[q,*[fmt(stat([r[k] for r in queue if r['qd']==q])[0]) for k in ['p50.000000','p95.000000','p99.000000','p99.900000']]] for q in sorted({8,knee})]),'',
 'Percentiles above are medians of per-run percentiles, not percentiles of a pooled distribution. Five-second trials provide limited evidence about rare stalls. QD1 is a low-queue baseline including OS/engine/device latency, not raw NAND latency or a guarantee of no background queue. SATA host/controller limits and flash parallelism can constrain throughput. No temperature trend, SLC-cache exhaustion, durability or steady-state claim is inferred from these tests.','']
 processed['ssd_trials']=len(ss)
lines += ['## Companion reports for this session','',
'- [Hardware counters](COUNTERS.md): measured core cycles per element, IPC, L1/L2 DTLB misses and demand DRAM fills per load, an AMAT-style fit and a page-walk cost estimate. Invariant TSC ticks are shown beside core cycles, never relabeled as them.',
'- [SIMD extension](SIMD-EXTENSION.md): int32 versus float32/float64, a three-point stencil, and a gather-indexed loop (negative case) with a forced hardware-gather control.',
'- [SSD extension](SSD-EXTENSION.md): block-size sweep, read/write mix, data pattern, buffered versus direct I/O (cold and warm cache), and a 40 GiB sustained write showing the SLC-cache sawtooth.',
'- [Optional GPU comparison](GPU.md): kernel-only versus end-to-end AXPY on a GTX 1660 Ti.','',
'- [Large pages](LARGE-PAGES.md): 4 KiB versus 2 MiB pages for the same chains (the main timing session had no lock-pages privilege; it was granted afterwards), plus the same study on a busy machine as a benchmark pitfall.','',
'## Student review','',
'The original [rubric audit](../../docs/RUBRIC.md) and [submission gates](../../docs/SUBMISSION-GATES.md) distinguish conditional features from required evidence. The student must independently review, test and understand the work before submission. AI assistance is described in [the disclosure](../../docs/AI-USE.md); no independent student checks are inferred from AI-executed runs.']
(P/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');(P/'summary.json').write_text(json.dumps(processed,indent=2));print(processed)
