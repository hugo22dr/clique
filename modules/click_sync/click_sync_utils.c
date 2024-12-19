#include <linux/kernel.h>
#include <linux/smp.h>
#include <asm/msr.h>
#include "click_sync_utils.h"
#include "click_sync_types.h"

static DEFINE_PER_CPU(u64, tsc_offset);

u64 read_tsc_synchronized(void) {
    u64 tsc;
    unsigned long flags;
    
    local_irq_save(flags);
    tsc = rdtsc();
    local_irq_restore(flags);
    
    return tsc;
}

// Nova função para ler TSC de uma CPU específica
u64 read_tsc_from_cpu(int cpu) {
    u64 tsc;
    unsigned long flags;
    
    local_irq_save(flags);
    
    if (cpu == smp_processor_id()) {
        tsc = rdtsc();
    } else {
        tsc = rdtsc() + per_cpu(tsc_offset, cpu);
    }
    
    local_irq_restore(flags);
    return tsc;
}

int get_ryzen_core_id(int thread_id) {
    int total_cores = num_online_cpus();
    int physical_cores = total_cores / 2;
    int ccx_id = thread_id / CCX_SIZE;
    int local_core = thread_id % CCX_SIZE;
    int physical_core = ((ccx_id * CCX_SIZE) + local_core + 1) % physical_cores;
    return (thread_id & 1) ? physical_core : physical_core + physical_cores;
}

u64 ns_to_tsc(u64 ns) {
    return (ns * sync_info->tsc_khz) >> 10;
}

void calibrate_tsc_wrapper(void *info) {
    u64 *tsc = (u64 *)info;
    *tsc = read_tsc_synchronized();
}

void calibrate_tsc_offsets(void) {
    int cpu;
    u64 base_tsc, cpu_tsc;

    base_tsc = read_tsc_synchronized();
    
    for_each_online_cpu(cpu) {
        if (cpu == 0) {
            per_cpu(tsc_offset, cpu) = 0;
            continue;
        }
        
        smp_call_function_single(cpu, calibrate_tsc_wrapper, &cpu_tsc, true);
        per_cpu(tsc_offset, cpu) = cpu_tsc - base_tsc;
    }
}