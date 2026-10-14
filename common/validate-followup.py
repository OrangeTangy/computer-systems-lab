"""Validate matrix coverage, units, provenance and SSD data for a completed session."""
import collections,hashlib,json,math,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[1];P=R/'sessions'/sys.argv[1]
def rows(name):return [json.loads(x) for x in (P/name).read_text().splitlines()]
def check(name,keys,total):
 rr=rows(name);assert len(rr)==total,(name,len(rr),total)
 assert all(r['correct'] for r in rr)
 assert sorted(r['sequence'] for r in rr)==list(range(total))
 counts=collections.Counter(tuple(r[k] for k in keys) for r in rr);assert set(counts.values())=={5}
 assert all(set(r['trial'] for r in rr if tuple(r[k] for k in keys)==group)==set(range(5)) for group in counts)
 return rr
s=check('simd.jsonl',['dtype','build','kind','n','stride','offset_elements'],840)
for r in s:
 e=r['n']*r['reps'];assert r['max_error']<=r['tolerance'];assert math.isclose(r['ns_element'],r['seconds']*1e9/e,abs_tol=.001)
 assert math.isclose(r['gflops'],e*(1 if r['kind']==1 else 2)/r['seconds']/1e9,abs_tol=.001)
b=check('bandwidth.jsonl',['n'],10)
for r in b:assert math.isclose(r['useful_GB_s'],12*r['n']*r['passes']/r['seconds']/1e9,abs_tol=.001)
m=check('latency.jsonl',['bytes','pattern'],210)
for r in m:assert r['pinned'] and r['cpu']==0 and math.isclose(r['ns_per_op'],r['elapsed_s']*1e9/r['operations'],abs_tol=.001)
l=check('loaded.jsonl',['workers','read_percent'],105)
for r in l:assert math.isclose(r['latency_ns'],r['probe_seconds']*1e9/r['loads'],abs_tol=.001)
env=json.loads((P/'environment.json').read_text());loadenv=json.loads((P/'load-environment.json').read_text())
masks=[next(c['logical_cpu_mask'] for c in env['cores']['physical_cores'] if c['logical_cpu_mask']&(1<<cpu)) for cpu in [0,*loadenv['worker_cpus']]]
assert len(set(masks))==len(masks)
for build in json.loads((P/'builds.json').read_text()):
 src=P/'sources'/pathlib.Path(build['command'][-3]).name
 assert hashlib.sha256(src.read_bytes()).hexdigest()==build['source_sha256'],str(src)
assert hashlib.sha256((P/'sources/loaded-followup.c').read_bytes()).hexdigest()==loadenv['source_sha256']
index=rows('ssd/index.jsonl');assert len(index)==65
assert len({r['name'] for r in index})==65
assert set(collections.Counter((r['study'],r['rw'],r['bs_kib'],r['qd']) for r in index).values())=={5}
assert {r['qd'] for r in index if r['study']=='queue'}=={1,2,4,8,16,32,64,128,256}
for row in index:
 raw=json.loads((P/'ssd/raw'/(row['name']+'.json')).read_text());job=raw['jobs'][0];assert job['error']==0
 d='read' if 'read' in row['rw'] else 'write';v=job[d];assert v['total_ios']>0 and v['bw_bytes']>0
 assert all(float(v['lat_ns']['percentile'][k])>0 for k in ['50.000000','95.000000','99.000000','99.900000'])
 # fio places options from [global] under 'global options' and per-job overrides under 'job options'.
 assert int(job.get('job options',{}).get('direct',raw['global options'].get('direct',0)))==1
for name in ['prepare','verify']:assert all(j['error']==0 for j in json.loads((P/'ssd/raw'/(name+'.json')).read_text())['jobs'])
assert json.loads((P/'ssd/environment.json').read_text())['test_file_removed'] and not (P/'ssd/scratch/disposable.bin').exists()
print('PASS: 840 SIMD, 10 matched-bandwidth, 210 latency, 105 load and 65 SSD trials; units, correctness, matrices, source hashes and file cleanup.')
