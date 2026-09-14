"""Build, validate, and collect immutable per-run JSON data. Python 3, GCC required."""
import argparse, datetime, hashlib, itertools, json, os, pathlib, platform, random, subprocess, shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--profile',choices=['smoke','pilot','full'],default='smoke')
p.add_argument('--cpu',type=int,default=0)
p.add_argument('--reps',type=int,default=None)
p.add_argument('--seconds',type=float,default=None)
a=p.parse_args()
reps=a.reps or {'smoke':1,'pilot':3,'full':7}[a.profile]
seconds=a.seconds or {'smoke':.015,'pilot':.08,'full':.3}[a.profile]
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=ROOT/'data'/'raw'/f'{a.profile}-{stamp}';out.mkdir(parents=True)
exe=ROOT/'build'/('membench.exe' if os.name=='nt' else 'membench');exe.parent.mkdir(exist_ok=True)
flags=['-O3','-std=c11','-Wall','-Wextra','-fno-lto']
cmd=['gcc',*flags,str(ROOT/'src'/'membench.c'),'-o',str(exe)]
subprocess.run(cmd,check=True)
shutil.copy2(ROOT/'src'/'membench.c',out/'membench.c')
shutil.copy2(__file__,out/'run.py')
env={'timestamp_utc':stamp,'profile':a.profile,'platform':platform.platform(),'processor':platform.processor(),
     'logical_cpus':os.cpu_count(),'cpu_pinned':a.cpu,'compiler':subprocess.check_output(['gcc','--version'],text=True),
     'build_command':cmd,'source_sha256':hashlib.sha256((ROOT/'src'/'membench.c').read_bytes()).hexdigest(),
     'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
     'repetitions':reps,'minimum_seconds_per_trial':seconds,'order_seed':4320,
     'frequency_policy':'not controlled; record before final runs','SMT':'not yet verified',
     'isolation':'affinity enforced; no exclusive core reservation','NUMA':'not controlled',
     'page_policy':'ordinary allocation; actual backing page size not verified'}
if os.name=='nt':
    import winreg,ctypes
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
        env['cpu_model']=winreg.QueryValueEx(key,'ProcessorNameString')[0]
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
    m=Memory();m.length=ctypes.sizeof(m)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):env['physical_memory_bytes']=m.total_phys
else:
    for name,command in [('lscpu',['lscpu']),('numa',['numactl','--hardware'])]:
        try:env[name]=subprocess.check_output(command,text=True,stderr=subprocess.STDOUT)
        except (OSError,subprocess.CalledProcessError) as e:env[name]=str(e)
    for name,path in [('governor',f'/sys/devices/system/cpu/cpu{a.cpu}/cpufreq/scaling_governor'),('SMT','/sys/devices/system/cpu/smt/active'),('perf_event_paranoid','/proc/sys/kernel/perf_event_paranoid')]:
        try:env[name]=pathlib.Path(path).read_text().strip()
        except OSError:env[name]='unavailable'
(out/'environment.json').write_text(json.dumps(env,indent=2))
sizes=([4096,1048576] if a.profile=='smoke' else [2**k for k in range(12,29 if a.profile=='full' else 27,2)])
cases=[]
for n in sizes:
    for stride,pattern in itertools.product([64,256,1024],['sequential','random']):
        if n>=stride*10:cases.append(('latency',n,stride,pattern,100))
    for stride,reads in itertools.product([8,64,256,1024],[0,50,70,100]):
        if n>=stride*10:cases.append(('bandwidth',n,stride,'sequential',reads))
# Interleave conditions/trials to reduce drift bias; every row retains actual sequence.
trials=[(case,rep) for rep in range(reps) for case in cases]
random.Random(4320).shuffle(trials)
with (out/'measurements.jsonl').open('w') as f:
    for index,(case,rep) in enumerate(trials):
        mode,n,stride,pattern,reads=case
        command=[str(exe),mode,str(n),str(stride),pattern,str(reads),str(seconds),str(a.cpu),str(4320+rep)]
        row=json.loads(subprocess.check_output(command,text=True)); assert row['correct']
        row.update(trial=rep,sequence=index,command=command)
        f.write(json.dumps(row)+'\n');f.flush()
        if (index+1)%25==0:print(f'{index+1}/{len(trials)} trials',flush=True)
print(out)
