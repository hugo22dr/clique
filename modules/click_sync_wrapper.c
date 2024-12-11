#define _GNU_SOURCE
#include <Python.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdio.h>
#include <sched.h>
#include <pthread.h>
#include <sys/mman.h>
#include <errno.h>

// Definições de comandos ioctl
#define CLICK_SYNC_MAGIC 'k'
#define CLICK_SYNC_SET_THREADS _IOW(CLICK_SYNC_MAGIC, 1, int)
#define CLICK_SYNC_WAIT        _IOW(CLICK_SYNC_MAGIC, 2, unsigned long)

// Configurações de otimização
#define MAX_CPU_CORES 32
#define RT_PRIORITY 99

// Variáveis globais do módulo
static int device_fd = -1;  // File descriptor do dispositivo
static int initialized = 0;  // Flag de inicialização
static cpu_set_t cpu_mask;  // Máscara de CPU para afinidade

// Função auxiliar para configurar prioridade RT e afinidade de CPU
static int setup_thread_attributes(void) {
    struct sched_param param;
    int ret;

    // Configura prioridade RT
    param.sched_priority = RT_PRIORITY;
    ret = pthread_setschedparam(pthread_self(), SCHED_FIFO, &param);
    if (ret != 0) {
        PyErr_Format(PyExc_RuntimeError,
                    "Falha ao configurar prioridade RT: %s", strerror(errno));
        return -1;
    }

    // Lock memória
    if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
        PyErr_Format(PyExc_RuntimeError,
                    "Falha ao fazer lock da memória: %s", strerror(errno));
        return -1;
    }

    return 0;
}

// Função setup_sync: Configura número de threads
static PyObject* setup_sync(PyObject* self, PyObject* args) {
    int num_threads;
    int ret;

    // Valida os argumentos
    if (!PyArg_ParseTuple(args, "i", &num_threads)) {
        PyErr_SetString(PyExc_ValueError, "Número de threads inválido");
        return NULL;
    }

    // Verifica se já está inicializado
    if (initialized) {
        close(device_fd);
    }

    // Abre o dispositivo
    device_fd = open("/dev/precise_sync", O_RDWR);
    if (device_fd < 0) {
        PyErr_Format(PyExc_RuntimeError,
                    "Falha ao abrir /dev/precise_sync: %s", strerror(errno));
        return NULL;
    }

    // Configuração inicial de thread
    ret = setup_thread_attributes();
    if (ret != 0) {
        close(device_fd);
        return NULL;
    }

    // Configura número de threads
    if (ioctl(device_fd, CLICK_SYNC_SET_THREADS, &num_threads) < 0) {
        close(device_fd);
        PyErr_Format(PyExc_RuntimeError,
                    "Falha ao configurar threads: %s", strerror(errno));
        return NULL;
    }

    initialized = 1;
    return Py_BuildValue("i", 1);
}

// Função wait_for_click: Aguarda sincronização
static PyObject* wait_for_click(PyObject* self, PyObject* args) {
    unsigned long result;

    // Verifica inicialização
    if (!initialized) {
        PyErr_SetString(PyExc_RuntimeError, "Módulo não inicializado");
        return NULL;
    }

    // Tenta sincronizar
    if (ioctl(device_fd, CLICK_SYNC_WAIT, &result) < 0) {
        PyErr_Format(PyExc_RuntimeError,
                    "Falha na sincronização: %s", strerror(errno));
        return NULL;
    }

    return Py_BuildValue("K", result);
}

// Função cleanup para o módulo
static void cleanup_sync(void* self) {
    if (initialized) {
        close(device_fd);
        initialized = 0;
    }
}

// Tabela de métodos Python
static PyMethodDef SyncMethods[] = {
    {"setup_sync", setup_sync, METH_VARARGS, "Setup sync"},
    {"wait_for_click", wait_for_click, METH_VARARGS, "Wait for click"},
    {NULL, NULL, 0, NULL}
};

// Definição do módulo Python
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "click_sync",          // Nome do módulo
    NULL,                  // Documentação
    -1,
    SyncMethods,
    NULL,                  // Slots
    NULL,                  // Traverse
    NULL,                  // Clear
    cleanup_sync           // Função de cleanup
};

// Inicialização do módulo Python
PyMODINIT_FUNC PyInit_click_sync(void) {
    return PyModule_Create(&moduledef);
}