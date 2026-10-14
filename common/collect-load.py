"""Append a new homogeneous physical-core loaded-latency study to a named session."""
import sys,pathlib,json,subprocess,random,hashlib,shutil,datetime
R=pathlib.Path(__file__).resolve().parents[1];out=R/'sessions'/sys.argv[1]
env=json.loads((out/'environment.json').read_text());cores=env['cores']['physical_cores']
cpus=[(c['logical_cpu_mask']&-c['logical_cpu_mask']).bit_length()-1 for c in cores]
if cpus[0]!=0 or len(cpus)<3:raise SystemExit('Need CPU0 and at least two other physical cores')
cpus=cpus[1:6];exe=out/'build/loaded.exe';source=R/'common/loaded-followup.c'
cmd=['gcc','-O3','-mavx2','-Wall','-Wextra',str(source),'-o',str(exe)]
subprocess.run(cmd,check=True);shutil.copy2(source,out/'sources'/source.name)
meta={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'probe_cpu':0,'worker_cpus':cpus,'probe_bytes':64*2**20,'worker_bytes_each':128*2**20,'worker_operations':'AVX2 32-byte read/write operations; percentages describe useful operations, not DRAM bus bytes','timer_seconds':1,'trial_count_per_condition':5,'frequency':'unchanged policy','isolation':'affinity, no exclusive reservation'}
(out/'load-environment.json').write_text(json.dumps(meta,indent=2))
cases=[(w,read) for w in range(1,len(cpus)+1) for read in [0,50,70,100]]+[(0,100)]
trials=[(c,t) for c in cases for t in range(5)];random.Random(14320).shuffle(trials)
with (out/'loaded.jsonl').open('x') as f:
 for i,((w,read),t) in enumerate(trials):
  row=json.loads(subprocess.check_output([str(exe),str(w),str(read),'1048576','64','1','0',','.join(map(str,cpus))],text=True));assert row['correct'];row.update(sequence=i,trial=t);f.write(json.dumps(row)+'\n');f.flush()
  if i%10==0:print(f'Loaded memory: {i+1}/{len(trials)}',flush=True)
