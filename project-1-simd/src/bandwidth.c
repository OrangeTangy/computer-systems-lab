#include <windows.h>
#include <immintrin.h>
#include <malloc.h>
#include <stdio.h>
#include <stdint.h>
static volatile float sink;
static double now(void){LARGE_INTEGER t,f;QueryPerformanceCounter(&t);QueryPerformanceFrequency(&f);return (double)t.QuadPart/f.QuadPart;}
__attribute__((noinline)) static float scan(const float *a,size_t n){
 __m256 s0=_mm256_setzero_ps(),s1=s0,s2=s0,s3=s0;
 for(size_t i=0;i<n;i+=32){s0=_mm256_add_ps(s0,_mm256_load_ps(a+i));s1=_mm256_add_ps(s1,_mm256_load_ps(a+i+8));s2=_mm256_add_ps(s2,_mm256_load_ps(a+i+16));s3=_mm256_add_ps(s3,_mm256_load_ps(a+i+24));}
 float lanes[8];_mm256_storeu_ps(lanes,_mm256_add_ps(_mm256_add_ps(s0,s1),_mm256_add_ps(s2,s3)));float total=0;for(int i=0;i<8;i++)total+=lanes[i];return total;
}
int main(void){if(!SetThreadAffinityMask(GetCurrentThread(),1))return 3;size_t n=64*1024*1024;float *a=_aligned_malloc(n*4,64);if(!a)return 4;for(size_t i=0;i<n;i++)a[i]=1;
 float answer=scan(a,n);if(answer!=(float)n)return 5;double begin=now(),elapsed;size_t passes=0;
 do{__asm__ __volatile__("":::"memory");sink=scan(a,n);passes++;elapsed=now()-begin;}while(elapsed<1.0);
 printf("{\"bytes_per_pass\":%zu,\"passes\":%zu,\"seconds\":%.9f,\"GB_s\":%.6f,\"correct\":true}\n",n*4,passes,elapsed,n*4.0*passes/elapsed/1e9);_aligned_free(a);return 0;}
