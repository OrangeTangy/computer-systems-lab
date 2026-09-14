"""Independent small-case oracle, unit checks, and invalid-argument rejection."""
import json,pathlib,subprocess,os
root=pathlib.Path(__file__).resolve().parents[1]
exe=root/'build'/('membench.exe' if os.name=='nt' else 'membench')
def run(mode,pattern,reads):
    return json.loads(subprocess.check_output([str(exe),mode,'4096','64',pattern,str(reads),'.01','0','4320'],text=True))
def oracle_order():
    order=list(range(64));x=4320;mask=(1<<64)-1
    for i in range(63,0,-1):
        x^=(x<<13)&mask;x^=x>>7;x^=(x<<17)&mask;x&=mask
        j=x%(i+1);order[i],order[j]=order[j],order[i]
    return order
records=[]
for pattern in ['sequential','random']:
    r=run('latency',pattern,100)
    order=list(range(64)) if pattern=='sequential' else oracle_order()
    assert r['checksum']==order[r['operations']%64]*64
    records.append(r)
for reads in [0,50,70,100]:
    r=run('bandwidth','sequential',reads)
    assert r['checksum']==sum(i+1 for i in range(64) if i%10<reads//10)
    records.append(r)
for r in records:
    assert r['correct'] and r['pinned']
    expected=r['elapsed_s']*1e9/r['operations']
    assert abs(r['ns_per_op']-expected)<1e-4
    assert abs(r['useful_GiB_s']-r['operations']*8/r['elapsed_s']/2**30)<1e-4
bad=subprocess.run([str(exe),'bandwidth','4096','64','random','100','.01','0','4320'],capture_output=True,text=True)
assert bad.returncode==2
print('PASS: independent permutation/checksum oracles, timing units, affinity, invalid-case rejection (6 executions).')
