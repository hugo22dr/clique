"""Constantes para o gerenciamento de memória."""
from enum import Enum, auto

class MemoryFlags:
    MCL_CURRENT = 1
    MCL_FUTURE = 2
    MCL_ONFAULT = 4

class IOPriority:
    IOPRIO_CLASS_RT = 1
    IOPRIO_WHO_PROCESS = 1
    IOPRIO_SET = 289

LIBC_PATHS = [
    'libc.so.6',
    'libc.so',
    '/lib/x86_64-linux-gnu/libc.so.6',
    '/usr/lib64/libc.so.6'
]