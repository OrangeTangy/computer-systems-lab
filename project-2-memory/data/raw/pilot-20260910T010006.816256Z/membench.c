#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <inttypes.h>
#ifdef _WIN32
#include <windows.h>
#include <malloc.h>
static double now(void) { LARGE_INTEGER t,f; QueryPerformanceCounter(&t); QueryPerformanceFrequency(&f); return (double)t.QuadPart/f.QuadPart; }
static int pin(int cpu) { return cpu>=0 && cpu<64 && SetThreadAffinityMask(GetCurrentThread(), (DWORD_PTR)1<<cpu)!=0; }
static void *allocbuf(size_t n) { return _aligned_malloc(n,4096); }
#define release _aligned_free
#else
#include <time.h>
#include <sched.h>
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC_RAW,&t); return t.tv_sec+t.tv_nsec*1e-9; }
static int pin(int cpu) { cpu_set_t set; CPU_ZERO(&set); if(cpu<0 || cpu>=CPU_SETSIZE)return 0; CPU_SET(cpu,&set); return sched_setaffinity(0,sizeof(set),&set)==0; }
static void *allocbuf(size_t n) { void *p=NULL; if(posix_memalign(&p,4096,n))return NULL; return p; }
#define release free
#endif
static volatile uint64_t sink;
static uint64_t rngstate;
static uint64_t rnd(void) { uint64_t x=rngstate; x^=x<<13; x^=x>>7; x^=x<<17; return rngstate=x; }
/* A compiler barrier preserves every repeated pass without making loads volatile. */
#define BARRIER() __asm__ __volatile__("" ::: "memory")
__attribute__((noinline)) static size_t chase(const unsigned char *a,size_t p,size_t count) {
    for(size_t i=0;i<count;i++) p=*(const size_t *)(a+p);
    return p;
}
/* Ten explicit operations per group: mix denotes useful READ operations percent.
   These are ordinary cached stores, so physical traffic includes write allocation. */
__attribute__((noinline)) static uint64_t stream(unsigned char *a,size_t nodes,size_t stride,int reads,uint64_t val) {
    uint64_t s=0;
    for(size_t i=0;i<nodes;i++) {
        uint64_t *p=(uint64_t *)(a+i*stride);
        if((int)(i%10)<reads) s+=*p; else *p=val;
    }
    return s;
}
int main(int argc,char **argv) {
    if(argc!=9) { fprintf(stderr,"usage: membench latency|bandwidth bytes stride sequential|random reads_percent seconds cpu seed\n"); return 2; }
    const char *mode=argv[1],*pattern=argv[4];
    size_t bytes=strtoull(argv[2],NULL,10),stride=strtoull(argv[3],NULL,10);
    int reads=atoi(argv[5]),cpu=atoi(argv[7]); double duration=atof(argv[6]);
    uint64_t seed=strtoull(argv[8],NULL,10); rngstate=seed?seed:1;
    int latency=!strcmp(mode,"latency"), random=!strcmp(pattern,"random");
    if((!latency && strcmp(mode,"bandwidth")) || (strcmp(pattern,"sequential") && !random) ||
       stride<8 || stride%8 || bytes<stride*10 || bytes%stride || duration<=0 ||
       (reads!=0 && reads!=50 && reads!=70 && reads!=100) || (!latency && random)) {
        fprintf(stderr,"invalid arguments (random bandwidth is not implemented)\n"); return 2;
    }
    if(!pin(cpu)) { fprintf(stderr,"CPU affinity failed for cpu %d\n",cpu); return 3; }
    size_t nodes=bytes/stride;
    unsigned char *a=allocbuf(bytes); if(!a)return 4;
    memset(a,0,bytes); /* first-touch all pages outside timed region */
    size_t start=0,p=0; uint64_t checksum=0,operations=0; int correct=1;
    if(latency) {
        size_t *order=malloc(nodes*sizeof(size_t)); if(!order){release(a);return 4;}
        for(size_t i=0;i<nodes;i++)order[i]=i;
        if(random)for(size_t i=nodes-1;i>0;i--){size_t j=rnd()%(i+1),t=order[i];order[i]=order[j];order[j]=t;}
        for(size_t i=0;i<nodes;i++)*(size_t *)(a+order[i]*stride)=order[(i+1)%nodes]*stride;
        start=order[0]*stride; p=start;
        /* Validate exactly one Hamiltonian cycle before timing. */
        unsigned char *seen=calloc(nodes,1); if(!seen){free(order);release(a);return 4;}
        for(size_t i=0;i<nodes;i++) {
            if(p>=bytes || p%stride || seen[p/stride]) {correct=0;break;}
            seen[p/stride]=1; p=*(size_t *)(a+p);
        }
        correct=correct && p==start; free(seen); free(order);
        p=chase(a,start,nodes); sink=p;
    } else {
        for(size_t i=0;i<nodes;i++)*(uint64_t *)(a+i*stride)=i+1;
        uint64_t expected=0;
        for(size_t i=0;i<nodes;i++)if((int)(i%10)<reads/10)expected+=i+1;
        checksum=stream(a,nodes,stride,reads/10,7);
        correct=checksum==expected;
        for(size_t i=0;i<nodes;i++)if((int)(i%10)>=reads/10 && *(uint64_t *)(a+i*stride)!=7)correct=0;
        sink=checksum;
    }
    if(!correct){fprintf(stderr,"correctness failed\n");release(a);return 5;}
    /* Batch at least 65536 loads to amortize timer calls for small footprints. */
    size_t batch=nodes<65536?65536:nodes;
    double begin=now(),elapsed; uint64_t passes=0;
    do {
        BARRIER();
        if(latency){p=chase(a,p,batch); operations+=batch;sink=p;}
        else {checksum=stream(a,nodes,stride,reads/10,7+(passes&1));sink=checksum;operations+=nodes;}
        passes++; elapsed=now()-begin;
    }while(elapsed<duration);
    if(latency) { size_t expected=chase(a,start,operations%nodes); correct=(expected==p); }
    printf("{\"mode\":\"%s\",\"pattern\":\"%s\",\"bytes\":%zu,\"stride\":%zu,\"nodes\":%zu,\"reads_percent\":%d,\"cpu\":%d,\"pinned\":true,\"seed\":%" PRIu64 ",\"elapsed_s\":%.9f,\"operations\":%" PRIu64 ",\"ns_per_op\":%.6f,\"useful_GiB_s\":%.6f,\"correct\":%s,\"checksum\":%" PRIu64 "}\n",
        mode,pattern,bytes,stride,nodes,reads,cpu,seed,elapsed,operations,elapsed*1e9/operations,operations*8.0/elapsed/1073741824.0,correct?"true":"false",latency?(uint64_t)p:checksum);
    release(a);return correct?0:5;
}
