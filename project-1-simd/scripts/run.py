import pathlib,subprocess,json,itertools,random,hashlib
R=pathlib.Path(__file__).resolve().parents[1];(R/'build').mkdir(exist_ok=True);(R/'data').mkdir(exist_ok=True)
flags={'scalar':['-O3','-fno-tree-vectorize','-ffp-contract=off'], 'auto':['-O3','-ffp-contract=off'], 'native':['-O3','-march=native','-ffp-contract=off']}
builds=[]
for dtype,build in itertools.product(['float','double'],flags):
 exe=R/'build'/f'{dtype}-{build}.exe';report=R/'data'/f'vectorization-{dtype}-{build}.txt'
 command=['gcc','-std=c11',*flags[build],'-DTYPE='+dtype,'-fopt-info-vec-all='+str(report),str(R/'src/simd.c'),'-o',str(exe)]
 subprocess.run(command,check=True);builds.append({'dtype':dtype,'build':build,'command':command,'source_sha256':hashlib.sha256((R/'src/simd.c').read_bytes()).hexdigest()})
 (R/'data'/f'disassembly-{dtype}-{build}.txt').write_text(subprocess.check_output(['objdump','-d',str(exe)],text=True))
(R/'data/builds.json').write_text(json.dumps(builds,indent=2))
cases=set()
for dtype,build,kind,n in itertools.product(['float','double'],flags,range(3),[1024,8192,65536,524288,4194304]):cases.add((dtype,build,kind,n,1,0))
# Cross aligned/misaligned and divisible/tail sizes, including short loops.
for dtype,build,n,offset in itertools.product(['float','double'],flags,[16,19,65536,65539],[0,1]):cases.add((dtype,build,0,n,1,offset))
for dtype,build,stride in itertools.product(['float','double'],flags,[2,4,8]):cases.add((dtype,build,1,524288,stride,0))
trials=[(c,rep) for c in sorted(cases) for rep in range(3)];random.Random(4320).shuffle(trials)
with (R/'data/raw.jsonl').open('w') as f:
 for index,(c,rep) in enumerate(trials):
  dtype,build,kind,n,stride,offset=c;cmd=[str(R/'build'/f'{dtype}-{build}.exe'),str(n),str(stride),str(offset),str(kind),'.06']
  row=json.loads(subprocess.check_output(cmd,text=True));row.update(dtype=dtype,build=build,trial=rep,sequence=index);f.write(json.dumps(row)+'\n');f.flush()
  if index%100==0:print(f'SIMD {index+1}/{len(trials)}',flush=True)
