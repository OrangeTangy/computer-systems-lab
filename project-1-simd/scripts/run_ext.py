"""Collect the SIMD extension: int32 type comparison, 3-point stencil and gather-indexed multiply.

python project-1-simd/scripts/run_ext.py SESSION [--gcc gcc] [--objdump objdump]
Writes sessions/SESSION/simd-extension/ (refuses an existing directory). Single-threaded, pinned to CPU0.
"""
import argparse,hashlib,json,pathlib,random,re,shutil,subprocess,sys,datetime
p=argparse.ArgumentParser();p.add_argument('session');p.add_argument('--gcc',default='gcc');p.add_argument('--objdump',default='objdump');p.add_argument('--trials',type=int,default=5);a=p.parse_args()
R=pathlib.Path(__file__).resolve().parents[2];src=R/'project-1-simd/src/simd_ext.c'
out=R/'sessions'/a.session/'simd-extension';out.mkdir(exist_ok=False)
for d in ['build','evidence']:(out/d).mkdir()
shutil.copy(src,out/'simd_ext.c');sha=lambda f:hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
(out/'HYPOTHESES.md').write_text('''# Predictions before the SIMD extension (written before collection)

- **int32 vs float32 vs float64 (z = 3x + y):** int32 and float32 both pack 8 lanes in a 256-bit register, so in-cache native speedups should be similar (about 4-8x over scalar) and float64 about half (4 lanes). From DRAM all three should converge toward the same bytes/second limit, so float64 should take about twice the time per element of the 32-bit types.
- **Stencil:** three loads of overlapping neighbors per output, but only one new cache line of input per 16 floats. It should vectorize with unaligned loads and gain more than AXPY in cache, because it does 5 operations per element with fewer bytes per operation (higher arithmetic intensity). It should still compress toward memory bandwidth from DRAM.
- **Gather with identity index:** the compiler cannot prove the index is contiguous, so it must use AVX2 `vgatherdps` (a compile check showed GCC 16 does emit gathers for this core under `-march=native`; SSE2 has no gather, so the `auto` build should stay scalar). Zen 3 gathers are microcoded and slow, so even with perfect locality the gather build may be no faster than scalar, and the `native-nogather` control (AVX2 allowed, gathers forbidden) isolates the gather instruction's cost.
- **Gather with random index:** once x exceeds the caches, each element is a random cache-line access; runtime should approach the dependent-free random-access rate and SIMD should provide almost no benefit (negative case).
''')
gcc=shutil.which(a.gcc) or a.gcc;objdump=shutil.which(a.objdump) or a.objdump
types={'int32':'int32_t','float':'float','double':'double'}
# native-nogather keeps AVX2 but forbids gather instructions, isolating the gather instruction's own cost.
variants={'scalar':['-fno-tree-vectorize'],'auto':[],'native':['-march=native'],'native-nogather':['-march=native','-mtune-ctrl=^use_gather_2parts,^use_gather_4parts,^use_gather_8parts']}
builds=[(t,v) for t in types for v in ['scalar','auto','native']]+[('float','native-nogather')]
meta={'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'compiler':subprocess.check_output([gcc,'--version'],text=True).splitlines()[0],'source_sha256':sha(src),'trials':a.trials,'builds':[]}
for t,v in builds:
 exe=out/'build'/f'ext-{t}-{v}.exe';cmd=[gcc,'-std=c11','-O3','-ffp-contract=off',f'-DTYPE={types[t]}',*variants[v],'-fopt-info-vec-all='+str(out/'evidence'/f'{t}-{v}-vector.txt'),str(src),'-o',str(exe)]
 subprocess.run(cmd,check=True)
 dis=subprocess.check_output([objdump,'-d','--no-show-raw-insn',str(exe)],text=True)
 kern={}
 for fn in ['axpy','stencil','gather']:
  m=re.search(rf'<{fn}>:\n(.*?)\n\n',dis,re.S);body=m.group(1) if m else ''
  kern[fn]={'instructions':len(body.splitlines()),'ymm':body.count('%ymm'),'xmm':body.count('%xmm'),'gather':len(re.findall(r'v(p)?gather',body)),
   'sample':[l.split('\t')[-1].strip() for l in body.splitlines() if re.search(r'gather|%ymm',l)][:6]}
 (out/'evidence'/f'{t}-{v}-kernels.json').write_text(json.dumps(kern,indent=1))
 meta['builds'].append({'dtype':t,'variant':v,'command':[pathlib.Path(c).name if i in (0,len(cmd)-3) else c for i,c in enumerate(cmd)],'binary_sha256':sha(exe),'kernels':{k:{x:kern[k][x] for x in ['ymm','xmm','gather']} for k in kern}})
(out/'environment.json').write_text(json.dumps(meta,indent=2))
sizes=[1024,32768,1048576,16777216]
cases=[(t,v,0,0,n) for t in types for v in ['scalar','auto','native'] for n in sizes]
cases+=[(t,v,3,0,n) for t in ['float','double'] for v in ['scalar','auto','native'] for n in sizes]
cases+=[('float',v,4,ix,n) for v in ['scalar','auto','native','native-nogather'] for ix in [0,1] for n in sizes]
trials=[(c,k) for c in cases for k in range(a.trials)];random.Random(4320).shuffle(trials)
with (out/'results.jsonl').open('x') as f:
 for i,((t,v,kind,ix,n),trial) in enumerate(trials):
  r=subprocess.run([str(out/'build'/f'ext-{t}-{v}.exe'),str(n),str(kind),str(ix),'0.2'],capture_output=True,text=True)
  if r.returncode:raise SystemExit(f'{t} {v} {kind} {ix} {n}: exit {r.returncode} {r.stderr}')
  row=json.loads(r.stdout);row.update(dtype=t,build=v,trial=trial,sequence=i);f.write(json.dumps(row)+'\n');f.flush()
  if i%40==0:print(f'SIMD extension: {i+1}/{len(trials)}',flush=True)
meta['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(out/'environment.json').write_text(json.dumps(meta,indent=2));print('done',len(trials))
