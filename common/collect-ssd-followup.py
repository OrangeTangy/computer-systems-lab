"""Same-session QD1-256 study on one disposable file. No raw device option.

python common/collect-ssd-followup.py SESSION /path/to/fio.exe
All original laptop data remains unchanged. About 8 minutes, predominantly reads.
"""
import datetime,json,pathlib,random,shutil,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parents[1];session=R/'sessions'/sys.argv[1]
out=session/'ssd';out.mkdir(exist_ok=False);fio=str(pathlib.Path(sys.argv[2]).resolve())
scratch=out/'scratch';scratch.mkdir();target=scratch/'disposable.bin'
if target.exists() or target.is_symlink():raise SystemExit('Refusing existing target')
if shutil.disk_usage(scratch).free<8*2**30:raise SystemExit('Need at least 8 GiB free')
for d in ['raw','configs']:(out/d).mkdir()
def capture(name,options):
 config='[global]\nioengine=windowsaio\nfilename=disposable.bin\ndirect=1\nthread=1\nnumjobs=1\ngroup_reporting=1\nsize=2G\nrandrepeat=1\nrandseed=14320\nrefill_buffers=1\nbuffer_compress_percentage=0\nlat_percentiles=1\nclat_percentiles=1\npercentile_list=50:95:99:99.9\n'+''.join(f'{k}={v}\n' for k,v in options.items())+f'\n[{name}]\n'
 path=out/'configs'/(name+'.fio');path.write_text(config);result=out/'raw'/(name+'.json')
 subprocess.run([fio,str(path),'--output-format=json','--output='+str(result)],cwd=scratch,check=True)
 data=json.loads(result.read_text());assert len(data['jobs'])==1 and data['jobs'][0]['error']==0
 return data
metadata={'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fio':subprocess.check_output([fio,'--version'],text=True).strip(),'repetitions':5,'runtime_seconds':5,'ramp_seconds':2,'file_bytes':2*2**30,'free_bytes_before':shutil.disk_usage(scratch).free,'direct':True,'numjobs':1,'host_metadata':'../environment.json','write_scope':'2 GiB prefill, 16 MiB verification, and QD1 write baselines on disposable file only','state':'active system drive, initialized file, no steady-state or raw-device-maximum claim'}
(out/'environment.json').write_text(json.dumps(metadata,indent=2))
(out/'HYPOTHESES.md').write_text('# Predictions before the SSD follow-up\n\nIncreasing random-read QD should initially raise IOPS, then add latency with smaller throughput gains. The operational knee is the first sampled QD reaching 90% of the within-session maximum median; uncertainty and non-monotonicity may make it ambiguous. p99.9 may vary strongly with short trials. One interleaved session avoids the historical QD128/256 session boundary, but cannot eliminate system-drive interference or establish steady state.\n')
capture('prepare',{'rw':'write','bs':'1M','iodepth':8,'end_fsync':1})
capture('verify',{'rw':'write','bs':'4k','iodepth':1,'size':'16M','verify':'crc32c','do_verify':1,'verify_fatal':1})
cases=[('queue','randread',4,q) for q in [1,2,4,8,16,32,64,128,256]]+[('baseline',p,b,1) for p,b in [('randread',4),('randwrite',4),('read',128),('write',128)]]
trials=[(c,t) for c in cases for t in range(5)];random.Random(14320).shuffle(trials)
with (out/'index.jsonl').open('x') as f:
 for i,((study,pattern,bs,qd),trial) in enumerate(trials):
  name=f'{i:03}-{study}-{pattern}-{bs}k-qd{qd}-t{trial}';begin=time.time()
  capture(name,{'rw':pattern,'bs':f'{bs}k','iodepth':qd,'time_based':1,'runtime':5,'ramp_time':2})
  f.write(json.dumps(dict(name=name,study=study,rw=pattern,bs_kib=bs,qd=qd,trial=trial,sequence=i,start_unix=begin))+'\n');f.flush()
  print(f'SSD follow-up: {i+1}/{len(trials)}',flush=True)
# Exact created file only; no recursive cleanup or arbitrary path accepted.
target.unlink();metadata['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();metadata['test_file_removed']=True
(out/'environment.json').write_text(json.dumps(metadata,indent=2));print('Disposable SSD file removed.',flush=True)
