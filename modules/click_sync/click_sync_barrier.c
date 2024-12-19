#include <linux/kernel.h>
#include <linux/sched.h>
#include <linux/delay.h>
#include <asm/msr.h>
#include "click_sync_barrier.h"
#include "click_sync_utils.h"

// Constantes otimizadas
#define BASE_MARGIN_NS 500ULL
#define MAX_RETRY_COUNT 3
#define CCX_SYNC_TIMEOUT_NS 100000ULL

// Estrutura para controle de TSC por CCX
struct ccx_sync_data {
    atomic_t ready_count;
    u64 max_tsc;
    spinlock_t lock;
} ____cacheline_aligned;

static DEFINE_PER_CPU(struct ccx_sync_data, ccx_sync);
static DEFINE_PER_CPU(u64, last_tsc);

// Função para verificar status do TSC
static bool verify_tsc_reliability(void) {
    u32 eax, ebx, ecx, edx;
    
    // Verifica invariant TSC
    cpuid(0x80000007, &eax, &ebx, &ecx, &edx);
    if (!(edx & (1 << 8))) {
        pr_warn("TSC não é invariante neste sistema\n");
        return false;
    }
    
    // Verifica constant TSC
    if (!boot_cpu_has(X86_FEATURE_CONSTANT_TSC)) {
        pr_warn("TSC não é constante neste sistema\n");
        return false;
    }
    
    return true;
}

// Função para sincronização adaptativa entre cores do mesmo CCX
static u64 sync_ccx_tsc(struct sync_thread *thread, u64 local_tsc) {
    struct ccx_sync_data *ccx_data;
    unsigned long flags;
    u64 ccx_max_tsc;
    int ccx_id = thread->ccx_id;
    
    ccx_data = this_cpu_ptr(&ccx_sync);
    spin_lock_irqsave(&ccx_data->lock, flags);
    
    // Atualiza TSC máximo do CCX
    if (local_tsc > ccx_data->max_tsc)
        ccx_data->max_tsc = local_tsc;
    
    if (atomic_inc_return(&ccx_data->ready_count) == CCX_SIZE) {
        ccx_max_tsc = ccx_data->max_tsc;
        atomic_set(&ccx_data->ready_count, 0);
        ccx_data->max_tsc = 0;
    } else {
        int retry = 0;
        u64 start_time = local_tsc;
        
        spin_unlock_irqrestore(&ccx_data->lock, flags);
        
        // Espera adaptativa com timeout
        while (retry++ < MAX_RETRY_COUNT) {
            u64 current_tsc = read_tsc_synchronized();
            if (current_tsc - start_time > ns_to_tsc(CCX_SYNC_TIMEOUT_NS)) {
                pr_warn("Timeout na sincronização do CCX %d\n", ccx_id);
                return local_tsc;
            }
            
            if (READ_ONCE(ccx_data->max_tsc) > 0) {
                ccx_max_tsc = READ_ONCE(ccx_data->max_tsc);
                break;
            }
            
            // Yield controlado
            if (retry > 1)
                usleep_range(100, 200);
        }
        return ccx_max_tsc;
    }
    
    spin_unlock_irqrestore(&ccx_data->lock, flags);
    return ccx_max_tsc;
}

static int wait_at_barrier_phase(struct sync_barrier_phase *phase,
                               struct sync_thread *thread,
                               int max_threads,
                               int phase_num) {
    unsigned long flags;
    int generation, ret = 0;
    u64 entry_tsc, target_tsc, sync_tsc;
    int retry_count = 0;
    
    local_irq_save(flags);
    preempt_disable();
    
    // Verifica confiabilidade do TSC
    if (!verify_tsc_reliability()) {
        ret = -EINVAL;
        goto out;
    }
    
    entry_tsc = read_tsc_synchronized();
    
    // Sincronização por CCX primeiro
    sync_tsc = sync_ccx_tsc(thread, entry_tsc);
    
    spin_lock_irqsave(&phase->lock, flags);
    
    generation = atomic_read(&phase->generation);
    this_cpu_write(last_tsc, sync_tsc);
    smp_wmb();
    
retry_barrier:
    if (atomic_inc_return(&phase->count) == max_threads) {
        u64 max_tsc = 0;
        int cpu;
        
        // Encontra TSC máximo considerando CCXs
        for_each_online_cpu(cpu) {
            u64 cpu_tsc = per_cpu(last_tsc, cpu);
            max_tsc = max(max_tsc, cpu_tsc);
        }
        
        // Margem adaptativa baseada na fase
        u64 margin = (phase_num == 2) ? 
                    BASE_MARGIN_NS : 
                    BASE_MARGIN_NS * (1ULL << phase_num);
                    
        target_tsc = max_tsc + ns_to_tsc(margin);
        
        WRITE_ONCE(phase->target_tsc, target_tsc);
        smp_wmb();
        
        atomic_set(&phase->count, 0);
        atomic_inc(&phase->generation);
        
        wake_up_all(&phase->waitq);
    } else {
        if (!wait_event_lock_irq_timeout(
                phase->waitq,
                generation != atomic_read(&phase->generation),
                phase->lock,
                msecs_to_jiffies(100))) {
            
            if (retry_count++ < MAX_RETRY_COUNT) {
                pr_warn("Retry %d na fase %d\n", retry_count, phase_num);
                goto retry_barrier;
            }
            ret = -ETIMEDOUT;
            goto out_unlock;
        }
        target_tsc = READ_ONCE(phase->target_tsc);
    }
    
    spin_unlock_irqrestore(&phase->lock, flags);
    
    // Busy wait otimizado para última fase
    if (phase_num == 2) {
        while (read_tsc_synchronized() < target_tsc) {
            if (!(read_tsc_synchronized() & 0x3)) {
                cpu_relax();
                if (read_tsc_synchronized() >= target_tsc)
                    break;
            }
        }
    } else {
        // Espera híbrida para outras fases
        while (read_tsc_synchronized() < target_tsc - ns_to_tsc(1000)) {
            usleep_range(1, 2);
        }
        while (read_tsc_synchronized() < target_tsc) {
            cpu_relax();
        }
    }
    
    goto out;
    
out_unlock:
    spin_unlock_irqrestore(&phase->lock, flags);
out:
    preempt_enable();
    local_irq_restore(flags);
    return ret;
}

int wait_at_barrier(struct sync_data *data, struct sync_thread *thread) {
    int ret;
    
    // Fase 1: Localização
    ret = wait_at_barrier_phase(&data->barrier.locate, thread,
                               data->max_threads, 0);
    if (ret) return ret;
    
    // Fase 2: Foco
    ret = wait_at_barrier_phase(&data->barrier.focus, thread,
                               data->max_threads, 1);
    if (ret) return ret;
    
    // Fase 3: Pré-clique
    return wait_at_barrier_phase(&data->barrier.pre_click, thread,
                               data->max_threads, 2);
}