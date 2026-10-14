/* A separate two-read/one-write streaming reference, same byte convention as SIMD. */
#include <windows.h>
#include <immintrin.h>
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>
static volatile float sink;
static double now(void){LARGE_INTEGER t,f;QueryPerformanceCounter(&t);QueryPerformanceFrequency(&f);return (double)t.QuadPart/f.QuadPart;}
__attribute__((noinline)) static void scan(float *restrict z,const float *restrict x,const float *restrict y,size_t n){
 for(size_t i=0;i<n;i+=8)_mm256_store_ps(z+i,_mm256_add_ps(_mm256_load_ps(x+i),_mm256_load_ps(y+i)));
}
int main(int argc,char **argv){
 if(argc!=2)return 2;size_t n=strtoull(argv[1],0,10);if(!n||n%8)return 2;
 if(!SetThreadAffinityMask(GetCurrentThread(),1))return 3;
 float *x=_aligned_malloc(n*4,64),*y=_aligned_malloc(n*4,64),*z=_aligned_malloc(n*4,64);if(!x||!y||!z)return 4;
 for(size_t i=0;i<n;i++){x[i]=(float)(i%31);y[i]=(float)(i%17);z[i]=0;}
 scan(z,x,y,n);for(size_t i=0;i<n;i++)if(z[i]!=x[i]+y[i])return 5;
 double t=now(),elapsed;size_t passes=0;
 do{__asm__ __volatile__("":::"memory");scan(z,x,y,n);sink=z[passes%n];passes++;elapsed=now()-t;}while(elapsed<.3);
 for(size_t i=0;i<n;i++)if(z[i]!=x[i]+y[i])return 5;
 printf("{\"n\":%zu,\"seconds\":%.9f,\"passes\":%zu,\"useful_GB_s\":%.6f,\"correct\":true}\n",n,elapsed,passes,12.0*n*passes/elapsed/1e9);
 _aligned_free(x);_aligned_free(y);_aligned_free(z);return 0;
}
