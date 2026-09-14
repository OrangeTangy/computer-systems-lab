"""Read-only QD128/256 measurements after a fresh 2 GiB file prefill.
Run after run.py. Marked as a supplemental session rather than interleaved originals.
"""
import pathlib,json,subprocess,sys,time,shutil
R=pathlib.Path(__file__).resolve().parents[1];fio=str(pathlib.Path(sys.argv[1]).resolve());scratch=R/'scratch';scratch.mkdir(exist_ok=True);target=scratch/'queue-extension.bin'
if target.exists():raise SystemExit('Refusing existing extension target')
if shutil.disk_usage(scratch).free<8*2**30:raise SystemExit('Insufficient free space')
def execute(name,opts):
 path=R/'configs'/(name+'.fio');path.write_text('[global]\nioengine=windowsaio\nfilename=queue-extension.bin\ndirect=1\nthread=1\nnumjobs=1\nsize=2G\nrandseed=4320\nrefill_buffers=1\nbuffer_compress_percentage=0\nlat_percentiles=1\npercentile_list=50:95:99:99.9\n'+''.join(f'{k}={v}\n' for k,v in opts.items())+'\n['+name+']\n')
 out=R/'data/raw'/(name+'.json');subprocess.run([fio,str(path),'--output-format=json','--output='+str(out)],cwd=scratch,check=True);assert all(j['error']==0 for j in json.loads(out.read_text())['jobs'])
execute('extension-prepare',{'rw':'write','bs':'1M','iodepth':8,'end_fsync':1})
with (R/'data/index.jsonl').open('a') as f:
 sequence=129
 for t in range(3):
  for qd in ([128,256] if t%2==0 else [256,128]):
   name=f'extension-qd{qd}-t{t}';start=time.time();execute(name,{'rw':'randread','bs':'4k','iodepth':qd,'time_based':1,'runtime':3,'ramp_time':1});f.write(json.dumps(dict(name=name,study='queue',rw='randread',bs_kib=4,qd=qd,read_percent=100,range_mib=2048,direct=1,trial=t,sequence=sequence,start_unix=start,session='supplemental'))+'\n');f.flush();sequence+=1;print(name,flush=True)
target.unlink()
