#define _GNU_SOURCE
#include <Python.h>
#include <time.h>
#include <sched.h>
#include <pthread.h>
#include <sys/mman.h>

typedef struct {
    uint64_t target_ns;
    pthread_barrier_t barrier;
    int num_threads;
} sync_data;

static sync_data* shared_data;

static void configure_thread(void) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    pthread_setaffinity_np(pthread_self(), sizeof(set), &set);
    
    struct sched_param param = {.sched_priority = 99};
    sched_setscheduler(0, SCHED_FIFO, &param);
}

static PyObject* setup_sync(PyObject* self, PyObject* args) {
    int num_threads;
    if (!PyArg_ParseTuple(args, "i", &num_threads))
        return NULL;
    
    mlockall(MCL_CURRENT | MCL_FUTURE);
    
    shared_data = mmap(NULL, sizeof(sync_data), 
                      PROT_READ | PROT_WRITE,
                      MAP_SHARED | MAP_ANONYMOUS | MAP_LOCKED, -1, 0);
    
    pthread_barrier_init(&shared_data->barrier, NULL, num_threads);
    shared_data->num_threads = num_threads;
    
    configure_thread();
    
    return Py_BuildValue("i", 1);
}

static PyObject* wait_for_click(PyObject* self, PyObject* args) {
    configure_thread();
    struct timespec ts;
    
    pthread_barrier_wait(&shared_data->barrier);
    
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    shared_data->target_ns = (ts.tv_sec * 1000000000ULL + ts.tv_nsec) + 5000000;  // 5ms
    
    while (1) {
        clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
        uint64_t now = ts.tv_sec * 1000000000ULL + ts.tv_nsec;
        if (now >= shared_data->target_ns)
            break;
        __asm__ volatile("pause" ::: "memory");
    }
    
    return Py_BuildValue("K", shared_data->target_ns);
}

static PyMethodDef SyncMethods[] = {
    {"setup_sync", setup_sync, METH_VARARGS, "Setup sync"},
    {"wait_for_click", wait_for_click, METH_VARARGS, "Wait for click"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "click_sync",
    NULL,
    -1,
    SyncMethods
};

PyMODINIT_FUNC PyInit_click_sync(void) {
    return PyModule_Create(&moduledef);
}