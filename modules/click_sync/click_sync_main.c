#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/device.h>
#include <linux/uaccess.h>
#include <linux/sched.h>
#include <linux/sched/rt.h>
#include <linux/delay.h>
#include "click_sync_types.h"
#include "click_sync_barrier.h"
#include "click_sync_utils.h"

static int major_number;
static struct class* click_sync_class = NULL;
static struct device* click_sync_device = NULL;
struct sync_data *sync_info = NULL;
static DEFINE_PER_CPU(struct sync_thread, sync_threads);

static enum hrtimer_restart sync_timer_callback(struct hrtimer *timer) {
    struct sync_data *data = container_of(timer, struct sync_data, sync_timer);
    wake_up_all(&data->wait_queue);
    return HRTIMER_NORESTART;
}

static long click_sync_ioctl(struct file *file, unsigned int cmd, unsigned long arg) {
    int ret = 0;
    int thread_id;
    struct thread_count tc;
    struct sync_thread *thread;
    struct sched_param param = { .sched_priority = MAX_RT_PRIO - 1 };
    unsigned long flags;

    if (!sync_info || !sync_info->initialized) {
        pr_err("Click Sync: Module not properly initialized\n");
        return -EAGAIN;
    }

    switch (cmd) {
        case CLICK_SYNC_SET_THREADS: {
            if (copy_from_user(&tc, (void __user *)arg, sizeof(tc))) {
                pr_err("Click Sync: Failed to copy thread count from user\n");
                return -EFAULT;
            }
            
            pr_debug("Click Sync: Received thread count request: %d\n", tc.count);
            
            if (!is_valid_thread_count(tc.count)) {
                pr_err("Click Sync: Invalid thread count %d\n", tc.count);
                return -EINVAL;
            }
            
            // Atualiza configuração de threads com spinlock
            spin_lock_irqsave(&sync_info->sync_lock, flags);
            sync_info->max_threads = tc.count;
            
            // Reset das barreiras
            atomic_set(&sync_info->barrier.locate.count, 0);
            atomic_set(&sync_info->barrier.locate.generation, 0);
            atomic_set(&sync_info->barrier.locate.ccx_status[0], 0);
            atomic_set(&sync_info->barrier.locate.ccx_status[1], 0);
            
            atomic_set(&sync_info->barrier.focus.count, 0);
            atomic_set(&sync_info->barrier.focus.generation, 0);
            atomic_set(&sync_info->barrier.focus.ccx_status[0], 0);
            atomic_set(&sync_info->barrier.focus.ccx_status[1], 0);
            
            atomic_set(&sync_info->barrier.pre_click.count, 0);
            atomic_set(&sync_info->barrier.pre_click.generation, 0);
            atomic_set(&sync_info->barrier.pre_click.ccx_status[0], 0);
            atomic_set(&sync_info->barrier.pre_click.ccx_status[1], 0);
            
            sync_info->barrier.active = true;
            
            spin_unlock_irqrestore(&sync_info->sync_lock, flags);
            
            pr_info("Click Sync: Thread count set to %d\n", tc.count);
            break;
        }

        case CLICK_SYNC_WAIT:
            local_irq_save(flags);
            preempt_disable();
            
            thread = this_cpu_ptr(&sync_threads);
            thread_id = atomic_inc_return(&sync_info->ready_count) - 1;
            
            if (thread_id >= sync_info->max_threads) {
                atomic_dec(&sync_info->ready_count);
                preempt_enable();
                local_irq_restore(flags);
                return -EAGAIN;
            }
            
            thread->thread_id = thread_id;
            thread->core_id = get_ryzen_core_id(thread_id);
            thread->ccx_id = thread->core_id / CCX_SIZE;
            
            ret = set_cpus_allowed_ptr(current, cpumask_of(thread->core_id));
            if (ret) {
                atomic_dec(&sync_info->ready_count);
                preempt_enable();
                local_irq_restore(flags);
                return ret;
            }
            
            current->policy = SCHED_FIFO;
            current->rt_priority = param.sched_priority;
            
            calibrate_tsc_offsets();
            
            ret = wait_at_barrier(sync_info, thread);
            if (ret) {
                atomic_dec(&sync_info->ready_count);
                preempt_enable();
                local_irq_restore(flags);
                return ret;
            }
            
            u64 current_tsc = read_tsc_synchronized();
            u64 target_tsc = current_tsc + ns_to_tsc(SYNC_TIMEOUT_NS);
            thread->tsc_deadline = target_tsc;
            
            while (read_tsc_synchronized() < target_tsc) {
                if (!(read_tsc_synchronized() & 0x3)) {
                    cpu_relax();
                    if (read_tsc_synchronized() >= target_tsc)
                        break;
                }
            }
            
            atomic_dec(&sync_info->ready_count);
            preempt_enable();
            local_irq_restore(flags);
            break;

        case CLICK_SYNC_ATOMIC: {
            struct sync_click_cmd *cmd;
            int i;
            
            // Aloca estrutura no heap
            cmd = kmalloc(sizeof(*cmd), GFP_KERNEL);
            if (!cmd) {
                pr_err("Click Sync: Failed to allocate memory for command\n");
                return -ENOMEM;
            }
            
            if (copy_from_user(cmd, (void __user *)arg, sizeof(*cmd))) {
                pr_err("Click Sync: Failed to copy click command from user\n");
                kfree(cmd);
                return -EFAULT;
            }
            
            if (cmd->num_clicks <= 0 || cmd->num_clicks > MAX_THREADS) {
                pr_err("Click Sync: Invalid number of clicks: %d\n", cmd->num_clicks);
                kfree(cmd);
                return -EINVAL;
            }
            
            spin_lock_irqsave(&sync_info->sync_lock, flags);
            
            cmd->sync_time = read_tsc_synchronized() + ns_to_tsc(SYNC_TIMEOUT_NS);
            atomic_set(&cmd->completed_clicks, 0);
            
            for (i = 0; i < cmd->num_clicks; i++) {
                struct click_data *click = &cmd->clicks[i];
                click->click_time = cmd->sync_time;
                atomic_set(&click->status, CLICK_READY);
                
                pr_debug("Click Sync: Prepared click %d, xpath: %.32s...\n", 
                        i, click->xpath);
            }
            
            spin_unlock_irqrestore(&sync_info->sync_lock, flags);
            
            if (copy_to_user((void __user *)arg, cmd, sizeof(*cmd))) {
                pr_err("Click Sync: Failed to copy result back to user\n");
                kfree(cmd);
                return -EFAULT;
            }
            
            kfree(cmd);
            return 0;
        }
            
        default:
            return -EINVAL;
    }
    
    return ret;
}

static struct file_operations fops = {
    .owner = THIS_MODULE,
    .unlocked_ioctl = click_sync_ioctl,
};

static int __init click_sync_init(void) {
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
    
    // Inicialização das três fases
    // Fase de localização
    spin_lock_init(&sync_info->barrier.locate.lock);
    init_waitqueue_head(&sync_info->barrier.locate.waitq);
    atomic_set(&sync_info->barrier.locate.count, 0);
    atomic_set(&sync_info->barrier.locate.generation, 0);
    atomic_set(&sync_info->barrier.locate.ccx_status[0], 0);
    atomic_set(&sync_info->barrier.locate.ccx_status[1], 0);
    
    // Fase de foco
    spin_lock_init(&sync_info->barrier.focus.lock);
    init_waitqueue_head(&sync_info->barrier.focus.waitq);
    atomic_set(&sync_info->barrier.focus.count, 0);
    atomic_set(&sync_info->barrier.focus.generation, 0);
    atomic_set(&sync_info->barrier.focus.ccx_status[0], 0);
    atomic_set(&sync_info->barrier.focus.ccx_status[1], 0);
    
    // Fase de pré-clique
    spin_lock_init(&sync_info->barrier.pre_click.lock);
    init_waitqueue_head(&sync_info->barrier.pre_click.waitq);
    atomic_set(&sync_info->barrier.pre_click.count, 0);
    atomic_set(&sync_info->barrier.pre_click.generation, 0);
    atomic_set(&sync_info->barrier.pre_click.ccx_status[0], 0);
    atomic_set(&sync_info->barrier.pre_click.ccx_status[1], 0);
    
    sync_info->barrier.active = false;
    sync_info->barrier.sync_count = 0;
    sync_info->barrier.timeout_count = 0;
    
    spin_lock_init(&sync_info->sync_lock);
    init_waitqueue_head(&sync_info->wait_queue);
    
    hrtimer_init(&sync_info->sync_timer, CLOCK_MONOTONIC_RAW, HRTIMER_MODE_REL);
    sync_info->sync_timer.function = sync_timer_callback;
    
    sync_info->tsc_khz = tsc_khz << 10;
    sync_info->max_threads = min(num_online_cpus(), MAX_THREADS);
    atomic_set(&sync_info->ready_count, 0);
    atomic_set(&sync_info->error_count, 0);
    atomic_set(&sync_info->timeout_count, 0);
    
    calibrate_tsc_offsets();
    
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
    
    sync_info->initialized = true;
    
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

static void __exit click_sync_exit(void) {
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