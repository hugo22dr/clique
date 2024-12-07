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

#define DEVICE_NAME "click_sync"
#define CLASS_NAME "click_sync_class"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Click Sync Team");
MODULE_DESCRIPTION("Kernel module for precise click synchronization");
MODULE_VERSION("1.0");

static int major_number;
static struct class* click_sync_class = NULL;
//static struct cdev click_sync_cdev;
static struct device* click_sync_device = NULL;

// Estrutura para sincronização
struct sync_data {
    atomic_t ready_count;
    atomic_t target_time_ns;
    struct mutex lock;
    wait_queue_head_t wait_queue;
    int max_threads;
};

static struct sync_data *sync_info;

// IOCTL commands
#define CLICK_SYNC_MAGIC 'k'
#define CLICK_SYNC_SET_THREADS _IOW(CLICK_SYNC_MAGIC, 1, int)
#define CLICK_SYNC_WAIT       _IOW(CLICK_SYNC_MAGIC, 2, unsigned long)

static long click_sync_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    int ret = 0;

    switch (cmd) {
        case CLICK_SYNC_SET_THREADS:
            if (get_user(sync_info->max_threads, (int __user *)arg))
                return -EFAULT;
            atomic_set(&sync_info->ready_count, 0);
            break;

        case CLICK_SYNC_WAIT:
            // Define prioridade RT máxima para o thread atual
            struct sched_param param = { .sched_priority = MAX_RT_PRIO - 1 };
            param.sched_priority = MAX_RT_PRIO - 1;
            sched_set_fifo(current);

            // Incrementa contador de threads prontos
            atomic_inc(&sync_info->ready_count);

            // Último thread define o tempo alvo
            if (atomic_read(&sync_info->ready_count) == sync_info->max_threads) {
                ktime_t now = ktime_get();
                atomic_set(&sync_info->target_time_ns, now + 5000000); // 5ms
                wake_up_all(&sync_info->wait_queue);
            }

            // Espera precisa
            wait_event(sync_info->wait_queue, 
                       ktime_get() >= atomic_read(&sync_info->target_time_ns));
            break;

        default:
            ret = -EINVAL;
    }

    return ret;
}

static struct file_operations fops = {
    .owner = THIS_MODULE,
    .unlocked_ioctl = click_sync_ioctl,
};

static int __init click_sync_init(void)
{
    // Aloca estrutura de sincronização
    sync_info = kzalloc(sizeof(struct sync_data), GFP_KERNEL);
    if (!sync_info)
        return -ENOMEM;
        
    mutex_init(&sync_info->lock);
    init_waitqueue_head(&sync_info->wait_queue);
    atomic_set(&sync_info->ready_count, 0);
    
    // Registra o dispositivo de caractere
    major_number = register_chrdev(0, DEVICE_NAME, &fops);
    if (major_number < 0) {
        kfree(sync_info);
        return major_number;
    }
    
    // Cria a classe do dispositivo
    click_sync_class = class_create(CLASS_NAME);
    if (IS_ERR(click_sync_class)) {
        unregister_chrdev(major_number, DEVICE_NAME);
        kfree(sync_info);
        return PTR_ERR(click_sync_class);
    }
    
    // Cria o dispositivo
    click_sync_device = device_create(click_sync_class, NULL, 
                                    MKDEV(major_number, 0), NULL, DEVICE_NAME);
    if (IS_ERR(click_sync_device)) {
        class_destroy(click_sync_class);
        unregister_chrdev(major_number, DEVICE_NAME);
        kfree(sync_info);
        return PTR_ERR(click_sync_device);
    }
    
    printk(KERN_INFO "Click Sync: module loaded\n");
    return 0;
}

static void __exit click_sync_exit(void)
{
    device_destroy(click_sync_class, MKDEV(major_number, 0));
    class_destroy(click_sync_class);
    unregister_chrdev(major_number, DEVICE_NAME);
    kfree(sync_info);
    printk(KERN_INFO "Click Sync: module unloaded\n");
}

module_init(click_sync_init);
module_exit(click_sync_exit);