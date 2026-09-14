#include <windows.h>
#include <cpuid.h>
#include <stdio.h>
int main(void){SYSTEM_INFO sys;GetSystemInfo(&sys);printf("{\"logical_cpus\":%lu,\"page_size\":%lu,\"large_page_minimum\":%llu,\"cores\":[",sys.dwNumberOfProcessors,sys.dwPageSize,(unsigned long long)GetLargePageMinimum());
 for(unsigned cpu=0;cpu<sys.dwNumberOfProcessors;cpu++){if(!SetThreadAffinityMask(GetCurrentThread(),(DWORD_PTR)1<<cpu))return 3;unsigned a,b,c,d;__cpuid_count(0x1a,0,a,b,c,d);printf("%s{\"cpu\":%u,\"core_type_hex\":\"%x\",\"caches\":[",cpu?",":"",cpu,a>>24);
 for(unsigned k=0;;k++){__cpuid_count(4,k,a,b,c,d);if(!(a&31))break;unsigned long long size=(unsigned long long)((b>>22)+1)*(((b>>12)&1023)+1)*((b&4095)+1)*(c+1);printf("%s{\"level\":%u,\"type\":%u,\"bytes\":%llu,\"line\":%u,\"max_sharing_ids\":%u}",k?",":"",(a>>5)&7,a&31,size,(b&4095)+1,((a>>14)&4095)+1);}printf("]}");}
 SIZE_T size=GetLargePageMinimum();void *p=VirtualAlloc(NULL,size,MEM_RESERVE|MEM_COMMIT|MEM_LARGE_PAGES,PAGE_READWRITE);DWORD error=p?0:GetLastError();if(p)VirtualFree(p,0,MEM_RELEASE);printf("],\"huge_page_allocation_ok\":%s,\"huge_page_error\":%lu}\n",p?"true":"false",error);return 0;}
