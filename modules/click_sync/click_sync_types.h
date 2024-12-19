#ifndef _CLICK_SYNC_TYPES_H
#define _CLICK_SYNC_TYPES_H

#include <linux/atomic.h>
#include <linux/spinlock.h>
#include <linux/wait.h>
#include <linux/hrtimer.h>

// Definições básicas
#define CLICK_SYNC_MAGIC 'k'
#define DEVICE_NAME "precise_sync"
#define CLASS_NAME "precise_sync_class"

// Constantes de configuração
#define MAX_THREADS 16
#define CLICK_BUFFER_SIZE 256
#define CCX_SIZE 6
#define SYNC_TIMEOUT_NS 5000ULL
#define TSC_DEADLINE_TIMER_NS 1500ULL
#define TSC_SAFETY_MARGIN 50ULL
#define SYNC_TIMEOUT_JIFFIES (HZ/200)
#define MAX_TSC_OFFSETS 32

// Status do clique
enum click_status {
    CLICK_PENDING = 0,
    CLICK_READY = 1,
    CLICK_EXECUTING = 2,
    CLICK_COMPLETED = 3,
    CLICK_FAILED = -1
};

// Estruturas para sincronização atômica
struct thread_count {
    int count;
} __attribute__((packed));

struct click_data {
    void __user *element_ptr;
    u64 click_time;
    int driver_id;
    char xpath[CLICK_BUFFER_SIZE];
    atomic_t status;
    u64 actual_click_time;
} __attribute__((packed));

struct sync_click_cmd {
    struct click_data clicks[MAX_THREADS];
    int num_clicks;
    u64 sync_time;
    atomic_t completed_clicks;
    u32 cmd_lock;
} __attribute__((packed));

// Estruturas internas do kernel
struct sync_barrier_phase {
    atomic_t count;
    atomic_t generation;
    atomic_t ccx_status[2];
    u64 target_tsc;
    spinlock_t lock;
    wait_queue_head_t waitq;
} ____cacheline_aligned;

struct barrier_control {
    struct sync_barrier_phase locate;
    struct sync_barrier_phase focus;
    struct sync_barrier_phase pre_click;
    bool active;
    u32 sync_count;
    u32 timeout_count;
    u64 last_sync_tsc;
    u64 target_tsc;
    u64 last_sync_time;
} ____cacheline_aligned;

struct sync_thread {
    int cpu_id;
    int core_id;
    int thread_id;
    int ccx_id;
    u64 tsc_deadline;
    bool waiting;
    atomic_t ready;
} ____cacheline_aligned;

struct sync_data {
    struct sync_thread threads[MAX_THREADS];
    atomic_t ready_count;
    atomic_t error_count;
    atomic_t timeout_count;
    struct barrier_control barrier;
    spinlock_t sync_lock;
    wait_queue_head_t wait_queue;
    struct hrtimer sync_timer;
    u64 tsc_khz;
    int max_threads;
    bool initialized;
} ____cacheline_aligned;

// IOCTL commands
#define CLICK_SYNC_SET_THREADS _IOW(CLICK_SYNC_MAGIC, 1, struct thread_count)
#define CLICK_SYNC_WAIT _IOW(CLICK_SYNC_MAGIC, 2, unsigned long)
#define CLICK_SYNC_ATOMIC _IOW(CLICK_SYNC_MAGIC, 3, struct sync_click_cmd)

// Helper functions
static inline bool is_valid_thread_count(int num_threads) {
    return num_threads > 0 && num_threads <= MAX_THREADS;
}

extern struct sync_data *sync_info;

#endif