"""Exceções customizadas para o gerenciador de memória."""

class MemoryManagerError(Exception):
    """Exceção base para erros do gerenciador de memória."""
    pass

class LibCError(MemoryManagerError):
    """Erro ao carregar ou configurar libc."""
    pass

class MemoryLockError(MemoryManagerError):
    """Erro ao tentar bloquear memória."""
    pass

class IOPriorityError(MemoryManagerError):
    """Erro ao configurar prioridade de I/O."""
    pass