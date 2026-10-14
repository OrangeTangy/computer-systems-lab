/* Read only: export CPU0 context switches and attached PMCs using Windows ETW API.
   Counter ordering must be verified against the recording profile/metadata. */
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
static const GUID thread_guid={0x3d6fa8d1,0xfe05,0x11d0,{0x9d,0xda,0x00,0xc0,0x4f,0xd7,0xba,0x7c}};
static unsigned long long events,pmcs;
static void WINAPI record(EVENT_RECORD *r){
 events++;
 if(r->BufferContext.ProcessorNumber!=0 || memcmp(&r->EventHeader.ProviderId,&thread_guid,sizeof(GUID)) || r->EventHeader.EventDescriptor.Opcode!=36 || r->UserDataLength<8)return;
 DWORD ids[2];memcpy(ids,r->UserData,8);
 printf("%lld,%lu,%lu",(long long)r->EventHeader.TimeStamp.QuadPart,ids[0],ids[1]);
 for(unsigned i=0;i<r->ExtendedDataCount;i++)if(r->ExtendedData[i].ExtType==EVENT_HEADER_EXT_TYPE_PMC_COUNTERS){
  unsigned count=r->ExtendedData[i].DataSize/8;const unsigned char *p=(void *)(uintptr_t)r->ExtendedData[i].DataPtr;
  for(unsigned j=0;j<count;j++){uint64_t v;memcpy(&v,p+j*8,8);printf(",%llu",(unsigned long long)v);}pmcs++;
 }
 printf("\n");
}
int main(int argc,char **argv){
 if(argc!=2)return 2;EVENT_TRACE_LOGFILEA log={0};log.LogFileName=argv[1];log.ProcessTraceMode=PROCESS_TRACE_MODE_EVENT_RECORD|PROCESS_TRACE_MODE_RAW_TIMESTAMP;log.EventRecordCallback=record;
 TRACEHANDLE h=OpenTraceA(&log);if(h==INVALID_PROCESSTRACE_HANDLE){fprintf(stderr,"OpenTrace error %lu\n",GetLastError());return 3;}
 fprintf(stderr,"frequency=%lld events_lost=%lu buffers_lost=%lu\n",(long long)log.LogfileHeader.PerfFreq.QuadPart,log.LogfileHeader.EventsLost,log.LogfileHeader.BuffersLost);
 printf("qpc,new_thread_id,old_thread_id,pmc_values_in_recording_order\n");
 ULONG error=ProcessTrace(&h,1,NULL,NULL);CloseTrace(h);
 fprintf(stderr,"ProcessTrace=%lu events=%llu cswitch_with_pmc=%llu\n",error,events,pmcs);
 return error?4:pmcs?0:5;
}
