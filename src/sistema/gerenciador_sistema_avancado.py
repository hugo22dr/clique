from concurrent.futures import ThreadPoolExecutor
import logging
import os

from .system_resources import get_system_resources
from .cpu_manager import CPUManager
from .memory_manager import MemoryManager
from .signal_handler import SignalHandler
from .process_cleaner import ProcessCleaner

class EnhancedSystemManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.resources = get_system_resources()
        
        # Inicializa gerenciadores modulares
        self.cpu_manager = CPUManager(logger)
        self.memory_manager = MemoryManager(logger)
        self.process_cleaner = ProcessCleaner(logger)
        
        # Configurações originais
        self.cpu_governors = {}
        
        # Executor de threads
        self.executor = None
        
        # Configuração inicial
        self._initialize_system()

    def optimize_cpu_affinity(self):
        """Wrapper para otimização de afinidade de CPU."""
        return self.cpu_manager.optimize_cpu_affinity(self.resources.logical_processors)

    def optimize_memory_settings(self):
        """Wrapper para otimização de configurações de memória."""
        self.memory_manager.memory_lock()
        self.memory_manager.configure_memory_settings()

    def _initialize_system(self):
        """Inicialização centralizada do sistema."""
        # Otimizações de CPU
        self.cpu_manager.configure_cpu_specific_settings()
        self.cpu_manager.optimize_cpu_affinity(self.resources.logical_processors)
        
        # Otimizações de memória
        self.memory_manager.memory_lock()
        self.memory_manager.configure_memory_settings()
        
        # Inicializa pool de threads
        self._initialize_thread_pool()

    def _initialize_thread_pool(self, tasks: int = 4):
        """Inicializa o pool de threads com otimização."""
        try:
            core_assignments = self.cpu_manager.assign_cores_for_tasks(
                tasks, 
                self.resources.logical_processors
            )
            
            self.executor = ThreadPoolExecutor(
                max_workers=tasks,
                thread_name_prefix="worker"
            )

            for idx, cores in enumerate(core_assignments):
                os.sched_setaffinity(idx, cores)
                self.logger.info(f"Thread {idx} configurada com afinidade: {cores}")

        except Exception as e:
            self.logger.error(f"Erro ao inicializar pool de threads: {e}")
            self.executor = ThreadPoolExecutor(max_workers=2)  # Fallback seguro

    def set_process_priority(self, priority: int = -10):
        """Define a prioridade do processo usando 'nice'."""
        try:
            pid = os.getpid()
            os.nice(priority)
            self.logger.info(f"Prioridade do processo configurada para {priority} com sucesso.")
        except PermissionError:
            self.logger.warning("Permissão negada ao configurar prioridade de processo. Tente rodar com sudo.")
        except Exception as e:
            self.logger.error(f"Erro ao configurar prioridade do processo: {e}")

    def graceful_shutdown(self):
        """Realiza desligamento gracioso com garantias extras."""
        self.logger.info("Iniciando procedimento de desligamento gracioso...")

        try:
            # Força término de processos Chrome primeiro
            self.process_cleaner.cleanup_chromium_processes()

            # Desliga thread pool
            if self.executor:
                self.executor.shutdown(wait=False)

            # Restaura configurações do sistema
            self.cpu_manager.restore_cpu_settings(self.cpu_governors)
            self.memory_manager.restore_memory_settings()

            self.logger.info("Desligamento gracioso completado")

        except Exception as e:
            self.logger.error(f"Erro durante shutdown: {e}")
        finally:
            # Força saída do programa
            os._exit(0)