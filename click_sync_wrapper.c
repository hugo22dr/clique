#define _GNU_SOURCE
#include <Python.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdio.h>

// Definições de comandos ioctl
#define CLICK_SYNC_MAGIC 'k'
#define CLICK_SYNC_SET_THREADS _IOW(CLICK_SYNC_MAGIC, 1, int)
#define CLICK_SYNC_WAIT        _IOW(CLICK_SYNC_MAGIC, 2, unsigned long)

static int device_fd = -1; // File descriptor do dispositivo

// Função setup_sync: Configura número de threads
static PyObject* setup_sync(PyObject* self, PyObject* args) {
    int num_threads;

    // Valida os argumentos
    if (!PyArg_ParseTuple(args, "i", &num_threads)) {
        PyErr_SetString(PyExc_ValueError, "Número de threads inválido");
        return NULL;
    }

    // Abre o dispositivo
    device_fd = open("/dev/click_sync", O_RDWR);
    if (device_fd < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Falha ao abrir /dev/click_sync");
        return NULL;
    }

    // Configura número de threads
    if (ioctl(device_fd, CLICK_SYNC_SET_THREADS, &num_threads) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Falha ao configurar threads");
        return NULL;
    }

    return Py_BuildValue("i", 1);
}

// Função wait_for_click: Aguarda sincronização
static PyObject* wait_for_click(PyObject* self, PyObject* args) {
    unsigned long result;

    if (ioctl(device_fd, CLICK_SYNC_WAIT, &result) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Falha na sincronização");
        return NULL;
    }

    return Py_BuildValue("K", result);
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
    "click_sync",  // Nome do módulo
    NULL,          // Documentação
    -1,
    SyncMethods
};

// Inicialização do módulo Python
PyMODINIT_FUNC PyInit_click_sync(void) {
    return PyModule_Create(&moduledef);
}
