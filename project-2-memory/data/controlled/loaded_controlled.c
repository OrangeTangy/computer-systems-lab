/* Controlled follow-up: P-core workers only; stop at 128 KiB chunks. Original loaded.c/data retained. */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>
#include <cpuid.h>
#include <immintrin.h>
static HANDLE start_event;static volatile LONG stop_flag;static volatile size_t sink;
static double now(void){LARGE_INTEGER a,b;QueryPerformanceCounter(&a);QueryPerformanceFrequency(&b);return (double)a.QuadPart/b.QuadPart;}
typedef struct{HANDLE ready;size_t bytes;int cpu,reads,ok,delay_us;double elapsed,start_time,end_time;uint64_t accesses;} Worker;
static DWORD WINAPI worker(void *arg){Worker *w=arg;w->ok=SetThreadAffinityMask(GetCurrentThread(),(DWORD_PTR)1<<w->cpu)!=0;size_t n=16*1024*1024;double *a=_aligned_malloc(n*8,4096);if(!a)w->ok=0;if(a)for(size_t i=0;i<n;i++)a[i]=1;
 SetEvent(w->ready);WaitForSingleObject(start_event,INFINITE);double begin=now();w->start_time=begin;size_t position=0;
 if(w->ok)while(!InterlockedCompareExchange(&stop_flag,0,0)){double s=0;for(size_t j=0;j<16384;j++){size_t i=position+j;if((int)(i%10)<w->reads/10)s+=a[i];else a[i]=2;}position=(position+16384)%n;__asm__ __volatile__(""::"x"(s):"memory");w->accesses+=16384;double until=now()+w->delay_us*1e-6;while(now()<until && !InterlockedCompareExchange(&stop_flag,0,0))_mm_pause();}
 w->end_time=now();w->elapsed=w->end_time-begin;if(a)_aligned_free(a);return 0;}
static uint64_t rng=4320;static uint64_t rnd(void){rng^=rng<<13;rng^=rng>>7;rng^=rng<<17;return rng;}
__attribute__((noinline)) static size_t chase(size_t *a,size_t p,size_t n){for(size_t i=0;i<n;i++)p=a[p];return p;}
int main(int argc,char **argv){
 if(argc!=7)return 2;
 int delay_us=atoi(argv[6]);int workers=atoi(argv[1]),reads=atoi(argv[2]);size_t nodes=strtoull(argv[3],0,10),stride=strtoull(argv[4],0,10);double seconds=atof(argv[5]);
 if(workers<0||workers>3||nodes<2||stride<8||stride%8||seconds<=0||delay_us<0)return 2;
 if(!SetThreadAffinityMask(GetCurrentThread(),1))return 3;
 size_t *a=_aligned_malloc(nodes*stride,4096),*order=malloc(nodes*sizeof(size_t));if(!a||!order)return 4;
 for(size_t i=0;i<nodes*stride/8;i++)a[i]=0;
 for(size_t i=0;i<nodes;i++)order[i]=i;
 for(size_t i=nodes-1;i;i--){size_t j=rnd()%(i+1),t=order[j];order[j]=order[i];order[i]=t;}
 for(size_t i=0;i<nodes;i++)a[order[i]*stride/8]=order[(i+1)%nodes]*stride/8;
 size_t begin_node=order[0]*stride/8,p=begin_node;for(size_t i=0;i<nodes;i++){if(p!=order[i]*stride/8)return 5;p=a[p];}if(p!=begin_node)return 5;
 free(order);p=chase(a,p,nodes);sink=p;
 Worker w[6]={0};HANDLE handles[6];start_event=CreateEvent(NULL,TRUE,FALSE,NULL);
 for(int i=0;i<workers;i++){w[i].cpu=2+i*2;w[i].reads=reads;w[i].delay_us=delay_us;w[i].ready=CreateEvent(NULL,TRUE,FALSE,NULL);handles[i]=CreateThread(NULL,0,worker,&w[i],0,NULL);if(!handles[i])return 6;WaitForSingleObject(w[i].ready,INFINITE);if(!w[i].ok)return 6;}
 double t=now();SetEvent(start_event);uint64_t ops=0;double elapsed;
 do{p=chase(a,p,65536);ops+=65536;sink=p;elapsed=now()-t;}while(elapsed<seconds);
 InterlockedExchange(&stop_flag,1);uint64_t traffic=0;double max_elapsed=elapsed,start_lag=0,end_overhang=0;
 for(int i=0;i<workers;i++){WaitForSingleObject(handles[i],INFINITE);traffic+=w[i].accesses*8;double lag=w[i].start_time-t,over=w[i].end_time-(t+elapsed);if(lag>start_lag)start_lag=lag;if(over>end_overhang)end_overhang=over;if(w[i].elapsed>max_elapsed)max_elapsed=w[i].elapsed;CloseHandle(handles[i]);CloseHandle(w[i].ready);}
 size_t expected=chase(a,begin_node,ops%nodes);int correct=p==expected;
 printf("{\"workers\":%d,\"read_percent\":%d,\"nodes\":%zu,\"stride\":%zu,\"probe_bytes\":%zu,\"probe_seconds\":%.9f,\"traffic_seconds\":%.9f,\"loads\":%llu,\"latency_ns\":%.6f,\"traffic_GB_s\":%.6f,\"delay_us\":%d,\"start_lag_us\":%.3f,\"end_overhang_us\":%.3f,\"correct\":%s}\n",workers,reads,nodes,stride,nodes*stride,elapsed,max_elapsed,(unsigned long long)ops,elapsed*1e9/ops,traffic/(elapsed+end_overhang)/1e9,delay_us,start_lag*1e6,end_overhang*1e6,correct?"true":"false");
 CloseHandle(start_event);_aligned_free(a);return correct?0:5;
}
