#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdint.h>
#include <windows.h>
#include <malloc.h>
#include <x86intrin.h>
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
 if(argc!=6)return 2;size_t n=strtoull(argv[1],0,10),stride=atoi(argv[2]),offset=atoi(argv[3]);int kind=atoi(argv[4]);double seconds=atof(argv[5]);
 if(!n||!stride||kind<0||kind>2||seconds<=0)return 2;
 if(!SetThreadAffinityMask(GetCurrentThread(),1))return 3;
 size_t count=n*stride+offset+16;real *xb=_aligned_malloc(count*sizeof(real),64),*yb=_aligned_malloc(count*sizeof(real),64),*zb=_aligned_malloc(count*sizeof(real),64);if(!xb||!yb||!zb)return 4;
 real *x=xb+offset,*y=yb+offset,*z=zb+offset;
 for(size_t i=0;i<count-offset;i++){x[i]=(real)((int)(i%31)-15)/32;y[i]=(real)((int)(i%17)-8)/16;z[i]=0;}
 double expected=0,absolute=0;for(size_t i=0;i<n;i++){double v=(double)x[i*stride]*y[i*stride];expected+=v;absolute+=fabs(v);}
 real answer=kernel(z,x,y,n,stride,kind);double err=0;
 if(kind==2)err=fabs((double)answer-expected);
 else for(size_t i=0;i<n;i++){double ref=kind==0?1.25*(double)x[i*stride]+y[i*stride]:(double)x[i*stride]*y[i*stride];double e=fabs(z[i*stride]-ref);if(e>err)err=e;}
 double tolerance=sizeof(real)==4?1e-5*(1+absolute):1e-12*(1+absolute);
 if(err>tolerance){fprintf(stderr,"reference mismatch %g > %g\n",err,tolerance);return 5;}
 unsigned aux;_mm_lfence();uint64_t ticks0=__rdtscp(&aux);_mm_lfence();double t=now(),elapsed;size_t reps=0;
 do{__asm__ __volatile__("":::"memory");answer=kernel(z,x,y,n,stride,kind);sink=kind==2?answer:z[(reps%n)*stride];reps++;elapsed=now()-t;}while(elapsed<seconds);
 _mm_lfence();uint64_t ticks1=__rdtscp(&aux);_mm_lfence();
 double elements=(double)n*reps,bytes_per=kind==2?2*sizeof(real):3*sizeof(real);
 printf("{\"n\":%zu,\"stride\":%zu,\"offset_elements\":%zu,\"kind\":%d,\"dtype_bytes\":%zu,\"seconds\":%.9f,\"reps\":%zu,\"ns_element\":%.6f,\"gflops\":%.6f,\"useful_GB_s\":%.6f,\"tsc_ticks_element\":%.6f,\"max_error\":%.12g,\"tolerance\":%.12g,\"correct\":true}\n",n,stride,offset,kind,sizeof(real),elapsed,reps,elapsed*1e9/elements,elements*(kind==1?1:2)/elapsed/1e9,elements*bytes_per/elapsed/1e9,(ticks1-ticks0)/elements,err,tolerance);
 _aligned_free(xb);_aligned_free(yb);_aligned_free(zb);return 0;
}
