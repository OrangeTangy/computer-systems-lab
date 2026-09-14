"""Validate retained measurements and local Markdown links without rerunning benchmarks."""
import pathlib,json,re,math,collections
R=pathlib.Path(__file__).resolve().parents[1]
def rows(p):return [json.loads(line) for line in p.read_text().splitlines()]
s=rows(R/'project-1-simd/data/raw.jsonl');assert len(s)==450 and all(r['correct'] for r in s)
assert all(r['max_error']<=r['tolerance'] for r in s)
assert all(abs(r['ns_element']-r['seconds']*1e9/(r['n']*r['reps']))<.002 for r in s)
c=collections.Counter((r['dtype'],r['build'],r['kind'],r['n'],r['stride'],r['offset_elements']) for r in s);assert set(c.values())=={3}
m=rows(R/'project-2-memory/data/extended.jsonl');assert len(m)==90 and all(r['correct'] for r in m)
assert all(abs(r['latency_ns']-r['probe_seconds']*1e9/r['loads'])<.002 for r in m)
controlled_path=R/'project-2-memory/data/controlled/raw.jsonl'
controlled=rows(controlled_path) if controlled_path.exists() else []
if controlled:
 assert len(controlled)==85 and all(r['correct'] for r in controlled)
 counts=collections.Counter((r['workers'],r['read_percent'],r['delay_us']) for r in controlled)
 assert len(counts)==17 and set(counts.values())=={5}
 assert all(r['workers'] in [0,3] and r['start_lag_us']>=0 and r['end_overhang_us']>=0 for r in controlled)
 assert all(abs(r['latency_ns']-r['probe_seconds']*1e9/r['loads'])<.002 for r in controlled)
 masks=json.loads((R/'common/core-masks.json').read_text(encoding='utf-8-sig'))['physical_cores']
 selected=[next(c['logical_cpu_mask'] for c in masks if c['logical_cpu_mask']&(1<<cpu)) for cpu in [0,2,4,6]]
 assert len(set(selected))==4
ssd=R/'project-3-ssd';idx=rows(ssd/'data/index.jsonl');assert len(idx)>=129
assert len({r['name'] for r in idx})==len(idx)
for row in idx:
 j=json.loads((ssd/'data/raw'/(row['name']+'.json')).read_text())['jobs'][0];assert j['error']==0
 assert j['read']['total_ios']+j['write']['total_ios']>0
for name in ['prepare','verify','device-state']:
 assert all(j['error']==0 for j in json.loads((ssd/'data/raw'/(name+'.json')).read_text())['jobs'])
broken=[]
for file in R.rglob('*.md'):
 for link in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
  if '://' in link or link.startswith('#'):continue
  target=link.split('#')[0]
  if target and not (file.parent/target).exists():broken.append((str(file.relative_to(R)),link))
assert not broken,broken
print(f'PASS: {len(s)} SIMD + {len(m)} extended memory + {len(controlled)} controlled memory + {len(idx)} SSD trials, correctness/unit checks, core placement, expected conditions, all local Markdown links.')
