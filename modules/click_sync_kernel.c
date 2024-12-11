#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/sched.h>
#include <linux/sched/rt.h>
#include <linux/hrtimer.h>
#include <linux/ktime.h>
#include <linux/mutex.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/spinlock.h>
#include <linux/preempt.h>
#include <linux/wait.h>
#include <linux/cpu.h>
#include <linux/irq.h>
#include <linux/delay.h>
#include <asm/msr.h>
#include <asm/tsc.h>
#include <uapi/linux/sched/types.h>

#define DEVICE_NAME "precise_sync"
#define CLASS_NAME "precise_sync_class"
#define MAX_THREADS 64
#define SYNC_TIMEOUT_NS 10000
#define TSC_DEADLINE_TIMER_NS 2500
#define CCX_SIZE 6

#define CLICK_SYNC_MAGIC 'k'
#define CLICK_SYNC_SET_THREADS _IOW(CLICK_SYNC_MAGIC, 1, int32_t)
#define CLICK_SYNC_WAIT _IOW(CLICK_SYNC_MAGIC, 2, uint64_t)

static int major_number;
static struct class* click_sync_class = NULL;
static struct device* click_sync_device = NULL;

struct sync_thread {
    int cpu_id;
    atomic_t ready;
    u64 tsc_start;
    u64 tsc_deadline;
    int core_id;
    int thread_id;
} ____cacheline_aligned;

struct sync_data {
    struct sync_thread threads[MAX_THREADS];
    atomic_t ready_count __attribute__((aligned(64)));
    atomic64_t target_time_ns __attribute__((aligned(64)));
    raw_spinlock_t sync_lock __attribute__((aligned(64)));
    int max_threads;
    wait_queue_head_t wait_queue;
    struct hrtimer sync_timer;
    u64 tsc_khz;
    struct cpumask reserved_cpus;
} ____cacheline_aligned;

static struct sync_data *sync_info;
static DEFINE_PER_CPU(struct sync_thread, sync_threads);
static DEFINE_PER_CPU(u64, tsc_offset);

static inline int get_ryzen_core_id(int thread_id) {
    int total_cores = num_online_cpus();
    int physical_cores = total_cores / 2;
    int ccx_id = thread_id / CCX_SIZE;
    int local_core = thread_id % CCX_SIZE;
    int physical_core = ((ccx_id * CCX_SIZE) + local_core + 1) % physical_cores;
    return (thread_id & 1) ? physical_core : physical_core + physical_cores;
}

static u64 read_tsc_synchronized(void)
{
    u64 tsc;
    unsigned long flags;

    local_irq_save(flags);
    tsc = rdtsc();
    local_irq_restore(flags);
    
    return tsc;
}

static inline u64 ns_to_tsc(u64 ns)
{
    return (ns * sync_info->tsc_khz) >> 10;
}

// Função wrapper para calibração TSC
static void calibrate_tsc_wrapper(void *info)
{
    u64 *tsc = (u64 *)info;
    *tsc = read_tsc_synchronized();
}

static void calibrate_tsc_offsets(void)
{
    int cpu;
    u64 base_tsc, cpu_tsc;

    base_tsc = read_tsc_synchronized();

    for_each_online_cpu(cpu) {
        if (cpu == 0) {
            per_cpu(tsc_offset, cpu) = 0;
            continue;
        }

        // Usa o wrapper para resolver o problema do cast
        smp_call_function_single(cpu, calibrate_tsc_wrapper, &cpu_tsc, true);
        per_cpu(tsc_offset, cpu) = cpu_tsc - base_tsc;
    }
}

static enum hrtimer_restart sync_timer_callback(struct hrtimer *timer)
{
    struct sync_data *data = container_of(timer, struct sync_data, sync_timer);
    wake_up_all(&data->wait_queue);
    return HRTIMER_NORESTART;
}

static long click_sync_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    int thread_id;
    u64 target_tsc, current_tsc;
    struct sync_thread *thread;
    struct sched_param param = { .sched_priority = MAX_RT_PRIO - 1 };
    unsigned long flags;
    int ret = 0;

    switch (cmd) {
        case CLICK_SYNC_SET_THREADS:
            // [Código anterior permanece o mesmo...]
            break;

        case CLICK_SYNC_WAIT:
            local_irq_save(flags);
            preempt_disable();
            
            raw_spin_lock(&sync_info->sync_lock);
            
            thread_id = atomic_read(&sync_info->ready_count);
            if (thread_id >= sync_info->max_threads) {
                raw_spin_unlock(&sync_info->sync_lock);
                local_irq_restore(flags);
                preempt_enable();
                return -EAGAIN;
            }
            
            thread = this_cpu_ptr(&sync_threads);
            thread->thread_id = thread_id;
            thread->core_id = get_ryzen_core_id(thread_id);
            
            ret = set_cpus_allowed_ptr(current, cpumask_of(thread->core_id));
            if (ret) {
                raw_spin_unlock(&sync_info->sync_lock);
                local_irq_restore(flags);
                preempt_enable();
                return ret;
            }
            
            // Substituindo sched_setscheduler por atribuição direta
            current->policy = SCHED_FIFO;
            current->rt_priority = param.sched_priority;
            
            // [Resto do código permanece o mesmo...]
            break;
            
        default:
            pr_warn("Click Sync: Unknown ioctl command %u\n", cmd);
            return -EINVAL;
    }
    
    return ret;
}

static struct file_operations fops = {
    .owner = THIS_MODULE,
    .unlocked_ioctl = click_sync_ioctl,
};

static int __init click_sync_init(void)
{
    int ret;
    struct sched_param param = { .sched_priority = MAX_RT_PRIO - 1 };

    pr_info("Click Sync: Initializing module for Ryzen optimization\n");
    
    sync_info = (struct sync_data *)kzalloc(
        sizeof(struct sync_data) + L1_CACHE_BYTES - 1,
        GFP_KERNEL | __GFP_ZERO
    );
    if (!sync_info) {
        pr_err("Click Sync: Failed to allocate memory\n");
        return -ENOMEM;
    }

    sync_info = (struct sync_data *)ALIGN((unsigned long)sync_info, L1_CACHE_BYTES);
    
    raw_spin_lock_init(&sync_info->sync_lock);
    init_waitqueue_head(&sync_info->wait_queue);
    
    hrtimer_init(&sync_info->sync_timer, CLOCK_MONOTONIC_RAW, HRTIMER_MODE_REL);
    sync_info->sync_timer.function = sync_timer_callback;
    
    sync_info->tsc_khz = tsc_khz << 10;
    sync_info->max_threads = num_online_cpus() * 2;
    atomic_set(&sync_info->ready_count, 0);
    
    calibrate_tsc_offsets();
    
    // Substituindo sched_setscheduler por atribuição direta
    current->policy = SCHED_FIFO;
    current->rt_priority = param.sched_priority;
    
    major_number = register_chrdev(0, DEVICE_NAME, &fops);
    if (major_number < 0) {
        pr_err("Click Sync: Failed to register char device\n");
        ret = major_number;
        goto error_chrdev;
    }
    
    click_sync_class = class_create(CLASS_NAME);
    if (IS_ERR(click_sync_class)) {
        pr_err("Click Sync: Failed to create class\n");
        ret = PTR_ERR(click_sync_class);
        goto error_class;
    }
    
    click_sync_device = device_create(click_sync_class, NULL,
                                    MKDEV(major_number, 0), NULL, DEVICE_NAME);
    if (IS_ERR(click_sync_device)) {
        pr_err("Click Sync: Failed to create device\n");
        ret = PTR_ERR(click_sync_device);
        goto error_device;
    }
    
    pr_info("Click Sync: Module loaded successfully - Optimized for AMD Ryzen (%d cores/%d threads)\n",
            num_online_cpus() / 2, sync_info->max_threads);
    return 0;

error_device:
    class_destroy(click_sync_class);
error_class:
    unregister_chrdev(major_number, DEVICE_NAME);
error_chrdev:
    kfree(sync_info);
    return ret;
}

static void __exit click_sync_exit(void)
{
    pr_info("Click Sync: Unloading module\n");
    hrtimer_cancel(&sync_info->sync_timer);
    device_destroy(click_sync_class, MKDEV(major_number, 0));
    class_destroy(click_sync_class);
    unregister_chrdev(major_number, DEVICE_NAME);
    kfree(sync_info);
    pr_info("Click Sync: Module unloaded successfully\n");
}

module_init(click_sync_init);
module_exit(click_sync_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Click Sync Team");
MODULE_DESCRIPTION("Kernel module for precise click synchronization - AMD Ryzen Optimized");
MODULE_VERSION("2.0");