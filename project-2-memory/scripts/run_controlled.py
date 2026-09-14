import pathlib,subprocess,json,random,hashlib,datetime,os
R=pathlib.Path(__file__).resolve().parents[1];out=R/'data/controlled';out.mkdir(exist_ok=True);exe=R/'build/loaded_controlled.exe'
cmd=['gcc','-O3','-Wall','-Wextra',str(R/'src/loaded_controlled.c'),'-o',str(exe)];subprocess.run(cmd,check=True)
if 'Family 6 Model 154 ' not in os.environ.get('PROCESSOR_IDENTIFIER',''):
 raise SystemExit('This follow-up fixes Alder Lake P-core placement. Reconfigure and verify affinity for a different CPU before running.')
topology_exe=R/'build/core-masks.exe'
subprocess.run(['gcc','-O2',str(R.parent/'common/core_masks.c'),'-o',str(topology_exe)],check=True)
fresh_topology=subprocess.check_output([str(topology_exe)],text=True)
(out/'core-masks.json').write_text(fresh_topology)
cores=json.loads(fresh_topology)['physical_cores']
masks=[next(c['logical_cpu_mask'] for c in cores if c['logical_cpu_mask']&(1<<cpu)) for cpu in [0,2,4,6]];assert len(set(masks))==4
cases=[(3,read,delay) for read in [0,50,70,100] for delay in [0,5,20,100]]+[(0,100,0)]
trials=[(case,t) for case in cases for t in range(5)];random.Random(16320).shuffle(trials)
(out/'environment.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'compiler_command':cmd,'source_sha256':hashlib.sha256((R/'src/loaded_controlled.c').read_bytes()).hexdigest(),'probe_cpu':0,'worker_cpus':[2,4,6],'distinct_physical_core_masks':masks,'repetitions':5,'minimum_probe_seconds':.5,'chunk_bytes':131072,'power_policy':'unchanged Balanced','isolation':'affinity, not exclusive reservation'},indent=2))
with (out/'raw.jsonl').open('w') as f:
 for i,((workers,read,delay),t) in enumerate(trials):
  row=json.loads(subprocess.check_output([str(exe),str(workers),str(read),'262144','64','.5',str(delay)],text=True));assert row['correct'];row.update(trial=t,sequence=i);f.write(json.dumps(row)+'\n');f.flush()
  if i%10==0:print(f'Controlled memory {i+1}/{len(trials)}',flush=True)
