/* Read-only ETW queries: retain actual configured source order, not guessed XML order. */
#include <windows.h>
#include <evntrace.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void){
 ULONG bytes=0,status=TraceQueryInformation(0,TraceProfileSourceListInfo,NULL,0,&bytes);
 if(status!=ERROR_INSUFFICIENT_BUFFER && status!=ERROR_SUCCESS){printf("source_query_error=%lu\n",status);return 2;}
 unsigned char *sources=calloc(1,bytes);status=TraceQueryInformation(0,TraceProfileSourceListInfo,sources,bytes,&bytes);
 if(status){printf("source_query_error=%lu\n",status);return 3;}
 EVENT_TRACE_PROPERTIES *sessions[64];ULONG count=0;
 for(int i=0;i<64;i++){sessions[i]=calloc(1,sizeof(EVENT_TRACE_PROPERTIES)+2048);sessions[i]->Wnode.BufferSize=sizeof(EVENT_TRACE_PROPERTIES)+2048;sessions[i]->LoggerNameOffset=sizeof(EVENT_TRACE_PROPERTIES);sessions[i]->LogFileNameOffset=sizeof(EVENT_TRACE_PROPERTIES)+1024;}
 status=QueryAllTracesA(sessions,64,&count);if(status){printf("session_query_error=%lu\n",status);return 4;}
 int found=0;
 for(ULONG i=0;i<count;i++){
  char *name=(char *)sessions[i]+sessions[i]->LoggerNameOffset;
  if(!strstr(name,"LabCounterCollector"))continue;
  ULONG counters[64],returned=0;status=TraceQueryInformation(sessions[i]->Wnode.HistoricalContext,TracePmcCounterListInfo,counters,sizeof(counters),&returned);
  printf("session=%s query_status=%lu returned_bytes=%lu\n",name,status,returned);
  if(status)continue;
  for(unsigned j=0;j<returned/sizeof(ULONG);j++){
   unsigned off=0;int match=0;
   while(off<bytes){PROFILE_SOURCE_INFO *src=(PROFILE_SOURCE_INFO *)(sources+off);
    if(src->Source==counters[j]){printf("index=%u source=%lu name=%ls\n",j,counters[j],src->Description);match=1;break;}
    if(!src->NextEntryOffset)break;off+=src->NextEntryOffset;
   }
   if(!match)printf("index=%u source=%lu name=UNRESOLVED\n",j,counters[j]);
  }
  found++;
 }
 for(int i=0;i<64;i++)free(sessions[i]);free(sources);return found?0:5;
}
