"""Implementação principal do gerenciador de memória."""
import os
import ctypes
import logging
from typing import Optional

from .constants import MemoryFlags, IOPriority, LIBC_PATHS
from .exceptions import LibCError, MemoryLockError, IOPriorityError
from .utils import run_with_sudo, set_sysfs_value

class MemoryManager:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.libc: Optional[ctypes.CDLL] = None
        self._initialize_libc()

    def _initialize_libc(self) -> None:
        """Inicializa a biblioteca C."""
        for path in LIBC_PATHS:
            try:
                self.libc = ctypes.CDLL(path)
                self._configure_syscalls()
                self.logger.info(f"[Sistema] libc carregada com sucesso de: {path}")
                break
            except OSError:
                continue

        if not self.libc:
            raise LibCError("Não foi possível encontrar a biblioteca libc")

    def _configure_syscalls(self) -> None:
        """Configura syscalls da libc."""
        try:
            self.libc.syscall.argtypes = [ctypes.c_long, ctypes.c_int, ctypes.c_int]
            self.libc.syscall.restype = ctypes.c_int
        except Exception as e:
            raise LibCError(f"Falha ao configurar syscalls: {e}")

    def lock_memory(self) -> bool:
        """Bloqueia memória para evitar swapping."""
        if not self.libc:
            raise MemoryLockError("libc não disponível")

        try:
            import resource
            resource.setrlimit(resource.RLIMIT_MEMLOCK, (-1, -1))
        except Exception as e:
            self.logger.debug(f"[Sistema] Aviso ao configurar limite de memória: {e}")

        try:
            flags = MemoryFlags.MCL_CURRENT | MemoryFlags.MCL_FUTURE | MemoryFlags.MCL_ONFAULT
            if self.libc.mlockall(flags) != 0:
                # Tenta sem MCL_ONFAULT
                flags = MemoryFlags.MCL_CURRENT | MemoryFlags.MCL_FUTURE
                if self.libc.mlockall(flags) != 0:
                    raise MemoryLockError("Falha ao bloquear memória")
            
            self._configure_memory_settings()
            return True
            
        except Exception as e:
            raise MemoryLockError(f"Erro ao bloquear memória: {e}")

    def _configure_memory_settings(self) -> None:
        """Configura parâmetros adicionais de memória."""
        # Configura swappiness
        success, message = set_sysfs_value('/proc/sys/vm/swappiness', '0')
        if success:
            self.logger.info("[Sistema] Swappiness configurado para 0")
        else:
            self.logger.warning(f"[Sistema] Falha ao configurar swappiness: {message}")

        # Configura THP
        success, message = set_sysfs_value(
            '/sys/kernel/mm/transparent_hugepage/enabled', 
            'never'
        )
        if success:
            self.logger.info("[Sistema] THP desativado com sucesso")
        else:
            self.logger.debug(f"[Sistema] Falha ao configurar THP: {message}")

    def set_io_priority(self) -> None:
        """Configura prioridade de I/O."""
        try:
            if hasattr(self.libc, 'syscall'):
                ioprio = (IOPriority.IOPRIO_CLASS_RT << 13) | 0
                result = self.libc.syscall(
                    IOPriority.IOPRIO_SET,
                    IOPriority.IOPRIO_WHO_PROCESS,
                    os.getpid(),
                    ioprio
                )
                if result != 0:
                    raise IOPriorityError("Falha na syscall de ioprio_set")
                self.logger.info("[Sistema] Prioridade de I/O configurada via syscall")
        except Exception as e:
            # Fallback para ionice
            success, message = run_with_sudo([
                'ionice', '-c', '1', '-n', '0', str(os.getpid())
            ])
            if success:
                self.logger.info("[Sistema] Prioridade de I/O configurada via ionice")
            else:
                raise IOPriorityError(f"Falha ao configurar prioridade de I/O: {message}")

    def cleanup(self) -> None:
        """Restaura configurações originais."""
        try:
            if self.libc and hasattr(self.libc, 'munlockall'):
                self.libc.munlockall()
                self.logger.info("[Sistema] Configurações de memória restauradas")

            # Restaura swappiness
            success, _ = set_sysfs_value('/proc/sys/vm/swappiness', '60')
            if success:
                self.logger.info("[Sistema] Swappiness restaurado para 60")

            # Restaura THP
            success, _ = set_sysfs_value(
                '/sys/kernel/mm/transparent_hugepage/enabled',
                'madvise'
            )
            if success:
                self.logger.info("[Sistema] THP restaurado para configuração padrão")

        except Exception as e:
            self.logger.error(f"[Sistema] Falha ao limpar configurações: {e}")