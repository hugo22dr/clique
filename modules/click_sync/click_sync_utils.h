#ifndef _CLICK_SYNC_UTILS_H
#define _CLICK_SYNC_UTILS_H

#include <linux/types.h>

u64 read_tsc_synchronized(void);
u64 read_tsc_from_cpu(int cpu);
int get_ryzen_core_id(int thread_id);
u64 ns_to_tsc(u64 ns);
void calibrate_tsc_offsets(void);
void calibrate_tsc_wrapper(void *info);

#endif