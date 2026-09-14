import pathlib,subprocess,json,itertools,random
R=pathlib.Path(__file__).resolve().parents[1];(R/'build').mkdir(exist_ok=True)
exe=R/'build/loaded.exe';subprocess.run(['gcc','-O3','-Wall',str(R/'src/loaded.c'),'-o',str(exe)],check=True)
cases=[('loaded',w,r,262144,64) for w,r in itertools.product([0,1,2,4,6],[0,50,70,100])]
cases += [('pages',0,100,n,s) for n,s in itertools.product([256,1024,4096,16384,65536],[64,4096])]
trials=[(c,t) for c in cases for t in range(3)];random.Random(6320).shuffle(trials)
with (R/'data/extended.jsonl').open('w') as f:
 for i,(c,t) in enumerate(trials):
  study,w,r,n,s=c;cmd=[str(exe),str(w),str(r),str(n),str(s),'.35'];row=json.loads(subprocess.check_output(cmd,text=True));assert row['correct'];row.update(study=study,trial=t,sequence=i);f.write(json.dumps(row)+'\n');f.flush()
  if i%10==0:print(f'Memory {i+1}/{len(trials)}',flush=True)
