"""Roofline with measured roofs and measured kernel points (float32, native AVX2 build).

python project-1-simd/scripts/roofline_measured.py SESSION
Uses the session's simd.jsonl, bandwidth.jsonl, simd-extension/results.jsonl and counters.json (for the clock).
Intensities use useful bytes (each array element read or written once), the same convention as the bandwidth reference.
"""
import json,pathlib,statistics,sys
R=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'common'));from charts import plot
S=R/'sessions'/sys.argv[1]
rows=lambda p:[json.loads(l) for l in p.read_text().splitlines()]
simd=rows(S/'simd.jsonl');ext=rows(S/'simd-extension/results.jsonl');band=rows(S/'bandwidth.jsonl')
counters=json.loads((S/'counters.json').read_text())
clock=statistics.median(r['counters']['TotalCycles']['lower']/r['scheduled_s']/1e9 for r in counters['records'])
med=lambda v:(statistics.median(v),min(v),max(v))
SMALL,LARGE=1024,16777216
def pts(n):
 out=[]
 for kind,name,ai in [(1,'multiply',1/12),(0,'AXPY',2/12),(2,'ordered dot',2/8)]:
  out.append((name,ai,med([r['gflops'] for r in simd if r['dtype']=='float' and r['build']=='native' and r['kind']==kind and r['n']==n and r['stride']==1 and r['offset_elements']==0])))
 out.append(('stencil',5/8,med([r['gops'] for r in ext if r['dtype']=='float' and r['build']=='native' and r['kind']==3 and r['n']==n])))
 return out
dram=med([r['useful_GB_s'] for r in band if r['n']==LARGE])[0]
# Empirical in-cache roof: the highest useful-byte rate any validated native float run reached at N=1,024.
l1=max(r['useful_GB_s'] for r in simd if r['dtype']=='float' and r['build']=='native' and r['n']==SMALL and r['stride']==1)
peak=32*clock  # two 256-bit FMA pipes x 8 float lanes x 2 FLOPs, at the measured clock
xs=[1/32,1/16,1/12,1/8,1/6,1/4,3/8,5/8,1,2,4,8,16]
roof=lambda bw:[(x,min(peak,bw*x),min(peak,bw*x),min(peak,bw*x)) for x in xs]
small,large=pts(SMALL),pts(LARGE)
plot(S/'figures'/'roofline-measured.svg','Measured roofline: Ryzen 5 5500, float32 AVX2','Useful arithmetic intensity (FLOP/byte, log2)','GFLOP/s (log10)',
 [(f'In-cache roof ({l1:.0f} GB/s)',roof(l1)),(f'DRAM roof ({dram:.1f} GB/s)',roof(dram)),
  ('Kernels, N=1,024 (L1)',[(ai,*v) for _,ai,v in small]),('Kernels, N=16.8M (DRAM)',[(ai,*v) for _,ai,v in large])],True,
 f'Flat roof: {peak:.0f} GFLOP/s = 2 FMA pipes x 8 lanes x 2 FLOP x {clock:.2f} GHz (measured). Points left to right: multiply, AXPY, dot, stencil.',
 subtitle='Measured roofs and kernel medians; whiskers = trial min-max',logy=True,points_only=('Kernels, N=1,024 (L1)','Kernels, N=16.8M (DRAM)'))
ridge=peak/dram
tab=[]
for (name,ai,s),(_,_,d) in zip(small,large):
 tab.append(f'| {name} | {ai:.3f} | {s[0]:.2f} | {100*s[0]/min(peak,l1*ai):.0f}% | {d[0]:.2f} | {100*d[0]/min(peak,dram*ai):.0f}% |')
L=['# Measured roofline (float32, native AVX2)','',
f'Everything on this plot is measured on the Ryzen host except the flat compute roof, which is the standard peak estimate evaluated at the **measured** clock: 2 FMA pipes x 8 float lanes x 2 FLOPs x {clock:.2f} GHz (median core clock from the TotalCycles counter during the benchmark runs) = **{peak:.0f} GFLOP/s**. The DRAM roof is the traffic-matched two-read/one-write reference at N={LARGE:,} (**{dram:.1f} GB/s** useful). The in-cache roof is the highest useful-byte rate reached by any validated native run at N={SMALL:,} ({l1:.0f} GB/s), so it is an achieved bound, not a hardware specification. Intensity counts useful bytes, the same convention as both bandwidth roofs; write-allocate traffic would lower the physical intensity of store kernels by about a quarter.','',
'![Measured roofline](figures/roofline-measured.svg)','',
'| Kernel | FLOP/byte | N=1,024 GFLOP/s | % of in-cache roof | N=16.8M GFLOP/s | % of DRAM roof |','|---|---:|---:|---:|---:|---:|',*tab,'',
f'**Reading it.** The ridge point is at {ridge:.1f} FLOP/byte against DRAM. Every kernel here is between 1/12 and 5/8 FLOP/byte, at least {ridge/(5/8):.0f}x to the left of the ridge, so from DRAM all of them are memory-bound regardless of vector width. That is why the multiply, AXPY and stencil DRAM points sit on or near the sloped roof and why native/scalar speedups compress toward 1x at large N.','',
f'In cache, AXPY defines the empirical roof, so its 99% is circular; multiply independently reaches {small[0][2][0]/min(peak,l1*small[0][1])*100:.0f}% of it. The stencil reaches only {small[3][2][0]/min(peak,l1*small[3][1])*100:.0f}%, although it has the highest useful intensity: it issues three overlapping loads of x per output vector, and useful-byte intensity counts x only once. In L1 the limit is load issue, not bytes from memory.','',
f'**The ordered dot product is latency-bound, not memory-bound.** It delivers {small[2][2][0]:.2f} GFLOP/s with N={SMALL:,} in L1 and {large[2][2][0]:.2f} GFLOP/s from DRAM: the same rate at a 16,000x larger working set. A memory-bound kernel would slow down by roughly the 12x gap between the two roofs. Each addition must wait for the previous one because the source fixes the summation order, so the rate is set by the floating-point add latency, a ceiling the roofline model does not draw. Quantitatively: {small[2][2][0]:.2f} GFLOP/s is {small[2][2][0]/2:.2f} G additions/s, or {clock/(small[2][2][0]/2):.1f} cycles per addition at {clock:.2f} GHz, matching Zen 3\'s documented 3-cycle floating-point add latency. Neither more bandwidth nor wider vectors can help this kernel; only reassociating the sum (several partial accumulators) can.','',
'Some DRAM points can exceed the reference by a few percent (the reference is an achieved bound, and kernels with fewer arrays get slightly better prefetch behavior); the table keeps the measured ratio rather than clipping it.']
(S/'ROOFLINE.md').write_text('\n'.join(L)+'\n',encoding='utf-8');print(f'clock {clock:.3f} GHz, peak {peak:.1f}, dram {dram:.2f}, l1 {l1:.1f}');print('\n'.join(tab))
