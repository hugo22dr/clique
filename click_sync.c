//
#include <Python.h>
#include <time.h>
#include <sched.h>
#include <pthread.h>
#include <sys/mman.h>
#include <stdint.h>

// Definição mínima de MAX_CPUS (ajuste conforme necessário)
#ifndef MAX_CPUS
#define MAX_CPUS 128
#endif

// Estrutura compartilhada entre threads
typedef struct {
    uint64_t target_ns;
    pthread_barrier_t barrier;
    int num_threads;
    int thread_to_cpu[MAX_CPUS];
    pthread_spinlock_t sync_lock;
} __attribute__((aligned(64))) sync_data;

// Declaração global da variável shared_data
static sync_data *shared_data = NULL;

// Declaração de função get_next_cpu
static int get_next_cpu(void) {
    static int current_cpu = 0;
    current_cpu = (current_cpu + 1) % MAX_CPUS;
    return current_cpu;
}

// Função dummy para setup_sync (implementação real deve ser feita)
static PyObject* setup_sync(PyObject* self, PyObject* args) {
    int num_threads;
    if (!PyArg_ParseTuple(args, "i", &num_threads)) {
        PyErr_SetString(PyExc_ValueError, "Número de threads inválido");
        return NULL;
    }

    if (shared_data == NULL) {
        shared_data = (sync_data *)mmap(NULL, sizeof(sync_data),
                                       PROT_READ | PROT_WRITE,
                                       MAP_SHARED | MAP_ANONYMOUS, -1, 0);
        if (shared_data == MAP_FAILED) {
            PyErr_SetString(PyExc_RuntimeError, "Falha ao mapear memória compartilhada");
            return NULL;
        }
        pthread_barrier_init(&shared_data->barrier, NULL, num_threads);
        shared_data->num_threads = num_threads;
    }

    Py_RETURN_NONE;
}

static PyObject* wait_for_click(PyObject* self, PyObject* args) {
    struct timespec ts;
    uint64_t now, target;
    const uint64_t SYNC_DELAY_NS = 50000; // 50μs

    // Configura afinidade de CPU
    cpu_set_t set;
    int cpu = get_next_cpu();
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    pthread_setaffinity_np(pthread_self(), sizeof(set), &set);

    // Configura prioridade RT
    struct sched_param param = { .sched_priority = 99 };
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &param);

    // Prefetch dados na cache
    __builtin_prefetch(&shared_data->target_ns);

    // Barreira de sincronização
    pthread_barrier_wait(&shared_data->barrier);

    // Timestamp preciso
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    now = ts.tv_sec * 1000000000ULL + ts.tv_nsec;

    // Define target com operação atômica
    target = now + SYNC_DELAY_NS;
    __atomic_store_n(&shared_data->target_ns, target, __ATOMIC_RELEASE);

    // Busy wait otimizado
    while (1) {
        uint64_t cycles_start, cycles_end;
        __asm__ volatile("rdtsc" : "=a" (cycles_start));

        clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
        now = ts.tv_sec * 1000000000ULL + ts.tv_nsec;

        if (now >= target) break;

        __asm__ volatile("rdtsc" : "=a" (cycles_end));

        if ((cycles_end - cycles_start) < 1000) {
            for (int i = 0; i < 10; i++) {
                __asm__ volatile("pause");
            }
        }
    }

    return Py_BuildValue("K", target);
}

// Define os métodos do módulo
static PyMethodDef SyncMethods[] = {
    {"setup_sync", setup_sync, METH_VARARGS, "Setup sync"},
    {"wait_for_click", wait_for_click, METH_VARARGS, "Wait for click"},
    {NULL, NULL, 0, NULL}
};

// Define o módulo Python
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "click_sync",  // Nome do módulo
    NULL,          // Documentação
    -1,
    SyncMethods
};

// Função de inicialização do módulo
PyMODINIT_FUNC PyInit_click_sync(void) {
    return PyModule_Create(&moduledef);
}
