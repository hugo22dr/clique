#define _GNU_SOURCE
#include <Python.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <time.h>

#define CLICK_SYNC_MAGIC 'k'
#define CLICK_SYNC_SET_THREADS _IOW(CLICK_SYNC_MAGIC, 1, int)
#define CLICK_SYNC_WAIT       _IOW(CLICK_SYNC_MAGIC, 2, unsigned long)

static int device_fd = -1;

static PyObject* setup_sync(PyObject* self, PyObject* args) {
    int num_threads;
    if (!PyArg_ParseTuple(args, "i", &num_threads))
        return NULL;
    
    // Abre o dispositivo
    device_fd = open("/dev/click_sync", O_RDWR);
    if (device_fd < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Falha ao abrir dispositivo de sincronização");
        return NULL;
    }
    
    // Configura número de threads
    if (ioctl(device_fd, CLICK_SYNC_SET_THREADS, &num_threads) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Falha ao configurar threads");
        return NULL;
    }
    
    return Py_BuildValue("i", 1);
}

static PyObject* wait_for_click(PyObject* self, PyObject* args) {
    unsigned long result;
    
    if (ioctl(device_fd, CLICK_SYNC_WAIT, &result) < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Falha na sincronização");
        return NULL;
    }
    
    return Py_BuildValue("K", result);
}

static PyObject* cleanup(PyObject* self, PyObject* args) {
    if (device_fd >= 0) {
        close(device_fd);
        device_fd = -1;
    }
    return Py_BuildValue("i", 1);
}

static PyMethodDef SyncMethods[] = {
    {"setup_sync", setup_sync, METH_VARARGS, "Inicializa sincronização"},
    {"wait_for_click", wait_for_click, METH_VARARGS, "Aguarda sincronização"},
    {"cleanup", cleanup, METH_VARARGS, "Limpa recursos"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "click_sync",
    "Módulo de sincronização kernel",
    -1,
    SyncMethods
};

PyMODINIT_FUNC PyInit_click_sync(void) {
    return PyModule_Create(&moduledef);
}