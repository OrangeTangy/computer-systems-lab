/* Does the per-repetition timer call in simd.c distort small-N results?
   Usage: timer_overhead MODE N
     MODE timer  : cost of one now() call exactly as simd.c defines it (QPC + QPF), N calls
     MODE perrep : AXPY kernel, timer read after every repetition (simd.c's loop)
     MODE batch  : AXPY kernel, one timer pair around N_REPS repetitions
   The kernel and now() are copied verbatim from ../src/simd.c (kind 0, stride 1, offset 0).
   Prints one JSON line. Pinned to CPU0. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <windows.h>
#include <malloc.h>
#ifndef TYPE
#define TYPE float
#endif
typedef TYPE real;
static volatile double sink;
static double now(void){LARGE_INTEGER t,f;QueryPerformanceCounter(&t);QueryPerformanceFrequency(&f);return (double)t.QuadPart/f.QuadPart;}
__attribute__((noinline)) static real kernel(real *restrict z,const real *restrict x,const real *restrict y,size_t n,size_t stride,int kind){
 real sum=0;
 if(kind==0)for(size_t i=0;i<n;i++)z[i*stride]=(real)1.25*x[i*stride]+y[i*stride];
 else if(kind==1)for(size_t i=0;i<n;i++)z[i*stride]=x[i*stride]*y[i*stride];
 else for(size_t i=0;i<n;i++)sum+=x[i*stride]*y[i*stride];
 return sum;
}
int main(int argc,char **argv){
 if(argc!=3)return 2;
 const char *mode=argv[1];size_t n=strtoull(argv[2],0,10);
 if(!n||!SetThreadAffinityMask(GetCurrentThread(),1))return 3;
 const double seconds=0.2;
 if(!strcmp(mode,"timer")){
  double t0=now(),t=t0;size_t calls=0;
  do{for(int k=0;k<1000;k++)t=now();calls+=1000;}while(t-t0<seconds);
  printf("{\"mode\":\"timer\",\"calls\":%zu,\"seconds\":%.9f,\"ns_per_call\":%.4f}\n",calls,t-t0,(t-t0)*1e9/calls);return 0;
 }
 real *x=_aligned_malloc((n+16)*sizeof(real),64),*y=_aligned_malloc((n+16)*sizeof(real),64),*z=_aligned_malloc((n+16)*sizeof(real),64);
 if(!x||!y||!z)return 4;
 for(size_t i=0;i<n;i++){x[i]=(real)((int)(i%31)-15)/32;y[i]=(real)((int)(i%17)-8)/16;z[i]=0;}
 kernel(z,x,y,n,1,0);
 for(size_t i=0;i<n;i++)if(fabs((double)z[i]-(1.25*(double)x[i]+y[i]))>1e-6)return 5;
 double t=now(),elapsed;size_t reps=0;
 if(!strcmp(mode,"perrep")){
  do{__asm__ __volatile__("":::"memory");kernel(z,x,y,n,1,0);sink=z[reps%n];reps++;elapsed=now()-t;}while(elapsed<seconds);
 }else if(!strcmp(mode,"batch")){
  /* Same body without the timer: read the clock only every 4096 repetitions. */
  do{for(int k=0;k<4096;k++){__asm__ __volatile__("":::"memory");kernel(z,x,y,n,1,0);sink=z[(reps+k)%n];}reps+=4096;elapsed=now()-t;}while(elapsed<seconds);
 }else return 2;
 printf("{\"mode\":\"%s\",\"n\":%zu,\"dtype_bytes\":%zu,\"reps\":%zu,\"seconds\":%.9f,\"ns_rep\":%.4f,\"ns_element\":%.6f,\"correct\":true}\n",mode,n,sizeof(real),reps,elapsed,elapsed*1e9/reps,elapsed*1e9/reps/n);
 _aligned_free(x);_aligned_free(y);_aligned_free(z);return 0;
}
