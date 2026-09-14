"""File-only Windows fio suite. Never accepts a device or arbitrary target path."""
import argparse,datetime,json,pathlib,random,shutil,subprocess,time
R=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--fio',required=True);p.add_argument('--seconds',type=int,default=3);p.add_argument('--reps',type=int,default=3);a=p.parse_args()
fio=str(pathlib.Path(a.fio).resolve());temp=R/'scratch';temp.mkdir(exist_ok=True);target=temp/'disposable-fio-test.bin'
if target.exists():raise SystemExit('Refusing existing test file. Inspect and remove only the prior disposable test file before rerunning.')
if shutil.disk_usage(temp).free<8*2**30:raise SystemExit('Need at least 8 GiB free space before allocating a 2 GiB test file.')
raw=R/'data/raw';raw.mkdir(exist_ok=True);configs=R/'configs';configs.mkdir(exist_ok=True)
(R/'data/tool-version.txt').write_text(subprocess.check_output([fio,'--version'],text=True))
def execute(name,opts):
 config='[global]\nioengine=windowsaio\nfilename=disposable-fio-test.bin\ndirect=1\nthread=1\nnumjobs=1\ngroup_reporting=1\nsize=2G\nrandrepeat=1\nrandseed=4320\nrefill_buffers=1\nbuffer_compress_percentage=0\npercentile_list=50:95:99:99.9\nlat_percentiles=1\nclat_percentiles=1\n'+''.join(f'{k}={v}\n' for k,v in opts.items())+f'\n[{name}]\n'
 path=configs/(name+'.fio');path.write_text(config);out=raw/(name+'.json')
 subprocess.run([fio,str(path),'--output-format=json','--output='+str(out)],cwd=temp,check=True)
 data=json.loads(out.read_text());assert all(j['error']==0 for j in data['jobs']);return data
# Fully write allocated range before reading it. Verify a smaller range separately.
execute('prepare',{'rw':'write','bs':'1M','iodepth':8,'end_fsync':1})
execute('verify',{'rw':'write','bs':'4k','iodepth':1,'size':'16M','verify':'crc32c','do_verify':1,'verify_fatal':1})
cases=set()
for pattern in ['read','write','randread','randwrite']:
 for bs in [4,16,32,64,128,256]:cases.add(('block',pattern,bs,8,100,2048,1))
for pattern,bs in [('randread',4),('randwrite',4),('read',128),('write',128)]:cases.add(('baseline',pattern,bs,1,100,2048,1))
for qd in [1,2,4,8,16,32,64]:cases.add(('queue','randread',4,qd,100,2048,1))
for mix in [0,50,70,100]:cases.add(('mix','randrw',4,8,mix,2048,1))
for size in [64,2048]:cases.add(('range','randread',4,8,100,size,1))
cases.add(('pitfall','randread',4,8,100,64,0));cases.add(('pitfall','randread',4,8,100,64,1))
trials=[(c,t) for c in sorted(cases) for t in range(a.reps)];random.Random(4320).shuffle(trials)
meta={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':a.seconds,'ramp_seconds':1,'reps':a.reps,'test_file_bytes':2*2**30,'direct_io_default':True,'seed':4320,'notes':'File on active Windows system SSD; short-run burst characterization, not steady-state certification. Temperature unavailable unless separately recorded.'}
(R/'data/method.json').write_text(json.dumps(meta,indent=2))
with (R/'data/index.jsonl').open('w') as f:
 for i,(case,trial) in enumerate(trials):
  study,rw,bs,qd,mix,size,direct=case;name=f'{i:03}-{study}-{rw}-{bs}k-qd{qd}-r{mix}-m{size}-d{direct}-t{trial}'
  opts={'rw':rw,'bs':str(bs)+'k','iodepth':qd,'rwmixread':mix,'size':str(size)+'M','direct':direct,'time_based':1,'runtime':a.seconds,'ramp_time':1}
  start=time.time();execute(name,opts);f.write(json.dumps(dict(name=name,study=study,rw=rw,bs_kib=bs,qd=qd,read_percent=mix,range_mib=size,direct=direct,trial=trial,sequence=i,start_unix=start))+'\n');f.flush()
  if i%10==0:print(f'SSD {i+1}/{len(trials)}',flush=True)
# Short time-series observation; no claim of SLC exhaustion or steady state.
execute('device-state',{'rw':'write','bs':'128k','iodepth':8,'time_based':1,'runtime':12,'write_bw_log':str(raw/'device-state'),'log_avg_msec':1000,'end_fsync':1})
# Delete only the exact disposable file created by this script, never a directory/device.
target.unlink();print('SSD completed; disposable file removed.')
