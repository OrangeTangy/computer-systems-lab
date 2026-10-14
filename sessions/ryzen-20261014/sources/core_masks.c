#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
int main(void){DWORD bytes=0;GetLogicalProcessorInformation(NULL,&bytes);SYSTEM_LOGICAL_PROCESSOR_INFORMATION *p=malloc(bytes);if(!p||!GetLogicalProcessorInformation(p,&bytes))return 1;int comma=0;printf("{\"physical_cores\":[");for(unsigned i=0;i<bytes/sizeof(*p);i++)if(p[i].Relationship==RelationProcessorCore){printf("%s{\"logical_cpu_mask\":%llu,\"smt\":%s}",comma++?",":"",(unsigned long long)p[i].ProcessorMask,p[i].ProcessorCore.Flags?"true":"false");}printf("]}\n");free(p);return 0;}
