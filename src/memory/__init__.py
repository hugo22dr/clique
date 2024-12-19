# src/memory/__init__.py
"""Módulo de gerenciamento de memória."""
from .manager import MemoryManager
from .exceptions import (
    MemoryManagerError,
    LibCError,
    MemoryLockError,
    IOPriorityError
)

# Explicitar o que está disponível para importação
__all__ = [
    'MemoryManager',
    'MemoryManagerError',
    'LibCError',
    'MemoryLockError',
    'IOPriorityError'
]