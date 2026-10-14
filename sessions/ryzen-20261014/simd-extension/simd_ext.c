/* SIMD extension kernels: 1D three-point stencil, int32 AXPY and a gather-indexed multiply.
   Usage: simd_ext N KIND INDEX SECONDS
     KIND 0: z[i] = 3*x[i] + y[i]                      (int32 type comparison; any TYPE)
     KIND 3: z[i] = a*x[i-1] + b*x[i] + c*x[i+1]       (stencil, i = 1..N-2)
     KIND 4: z[i] = x[idx[i]] * y[i]                   (gather-like; INDEX 0 identity, 1 random permutation)
   Validates against a double-precision reference before timing; prints one JSON line. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <windows.h>
#include <malloc.h>
#ifndef TYPE
#define TYPE float
#endif
typedef TYPE real;
#define IS_INT ((real)0.5==(real)0)
static volatile double sink;
static double now(void){LARGE_INTEGER t,f;QueryPerformanceCounter(&t);QueryPerformanceFrequency(&f);return (double)t.QuadPart/f.QuadPart;}
__attribute__((noinline)) static void axpy(real *restrict z,const real *restrict x,const real *restrict y,size_t n){for(size_t i=0;i<n;i++)z[i]=(real)3*x[i]+y[i];}
__attribute__((noinline)) static void stencil(real *restrict z,const real *restrict x,size_t n){for(size_t i=1;i+1<n;i++)z[i]=(real)0.25*x[i-1]+(real)0.5*x[i]+(real)0.25*x[i+1];}
__attribute__((noinline)) static void gather(real *restrict z,const real *restrict x,const real *restrict y,const int32_t *restrict idx,size_t n){for(size_t i=0;i<n;i++)z[i]=x[idx[i]]*y[i];}
static void run(int kind,real *z,const real *x,const real *y,const int32_t *idx,size_t n){if(kind==0)axpy(z,x,y,n);else if(kind==3)stencil(z,x,n);else gather(z,x,y,idx,n);}
int main(int argc,char **argv){
 if(argc!=5)return 2;
 size_t n=strtoull(argv[1],0,10);int kind=atoi(argv[2]),random_index=atoi(argv[3]);double seconds=atof(argv[4]);
 if(n<3||n>(size_t)INT32_MAX||(kind!=0&&kind!=3&&kind!=4)||seconds<=0)return 2;
 if(!SetThreadAffinityMask(GetCurrentThread(),1))return 3;
 real *x=_aligned_malloc(n*sizeof(real),64),*y=_aligned_malloc(n*sizeof(real),64),*z=_aligned_malloc(n*sizeof(real),64);int32_t *idx=_aligned_malloc(n*sizeof(int32_t),64);
 if(!x||!y||!z||!idx)return 4;
 // Small dyadic values are exact in float, double and int32 (int32 uses integers only).
 for(size_t i=0;i<n;i++){x[i]=IS_INT?(real)((int)(i%31)-15):(real)((int)(i%31)-15)/32;y[i]=IS_INT?(real)((int)(i%17)-8):(real)((int)(i%17)-8)/16;z[i]=0;idx[i]=(int32_t)i;}
 if(random_index){uint64_t s=4320;for(size_t i=n-1;i>0;i--){s=s*6364136223846793005ULL+1442695040888963407ULL;size_t j=(size_t)((s>>33)%(i+1));int32_t t=idx[i];idx[i]=idx[j];idx[j]=t;}}
 run(kind,z,x,y,idx,n);double err=0;
 for(size_t i=(kind==3);i<n-(kind==3);i++){double ref=kind==0?3.0*x[i]+y[i]:kind==3?0.25*x[i-1]+0.5*x[i]+0.25*x[i+1]:(double)x[idx[i]]*y[i];double e=fabs((double)z[i]-ref);if(e>err)err=e;}
 double tolerance=IS_INT?0:sizeof(real)==4?1e-5:1e-12;
 if(err>tolerance){fprintf(stderr,"reference mismatch %g > %g\n",err,tolerance);return 5;}
 double t=now(),elapsed;size_t reps=0;
 do{__asm__ __volatile__("":::"memory");run(kind,z,x,y,idx,n);sink=(double)z[1+reps%(n-2)];reps++;elapsed=now()-t;}while(elapsed<seconds);
 size_t work=kind==3?n-2:n;double elements=(double)work*reps;
 double flops=kind==3?5:kind==0?2:1,bytes=kind==3?2*sizeof(real):kind==0?3*sizeof(real):3*sizeof(real)+sizeof(int32_t);
 printf("{\"n\":%zu,\"kind\":%d,\"random_index\":%d,\"dtype_bytes\":%zu,\"integer\":%s,\"seconds\":%.9f,\"reps\":%zu,\"ns_element\":%.6f,\"gops\":%.6f,\"useful_GB_s\":%.6f,\"max_error\":%.12g,\"correct\":true}\n",
  n,kind,random_index,sizeof(real),IS_INT?"true":"false",elapsed,reps,elapsed*1e9/elements,elements*flops/elapsed/1e9,elements*bytes/elapsed/1e9,err);
 _aligned_free(x);_aligned_free(y);_aligned_free(z);_aligned_free(idx);return 0;
}
