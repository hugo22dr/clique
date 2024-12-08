from concurrent.futures import ThreadPoolExecutor
import os
import psutil
import ctypes
import signal
import time
from typing import List, Optional
from dataclasses import dataclass
from threading import Event
import logging

@dataclass
class SystemResources:
    total_cores: int
    logical_processors: int
    available_memory: int
    process_id: int

class EnhancedSystemManager:
    def __init__(self, logger):
        self.logger = logger
        self.resources = self._get_system_resources()
        self.shutdown_event = Event()
        self.executor = None
        self._initialize_thread_pool()
        self.register_signal_handlers()  # Este método é chamado aqui

    def register_signal_handlers(self) -> None:
        """Registra manipuladores de sinais para encerramento gracioso."""
        def handle_signal(signum, frame):
            self.logger.info(f"Recebido sinal {signum}. Iniciando desligamento gracioso...")
            self.graceful_shutdown()

        # Registra os sinais para captura
        signal.signal(signal.SIGINT, handle_signal)  # Ctrl+C
        signal.signal(signal.SIGTERM, handle_signal)  # Sinal de término padrão

        self.logger.info("Manipuladores de sinais registrados com sucesso.")

    def _get_system_resources(self) -> SystemResources:
        """Coleta informações sobre os recursos do sistema."""
        return SystemResources(
            total_cores=psutil.cpu_count(logical=False),
            logical_processors=psutil.cpu_count(logical=True),
            available_memory=psutil.virtual_memory().available,
            process_id=os.getpid()
        )

    def _initialize_thread_pool(self) -> None:
        """Inicializa o pool de threads."""
        optimal_workers = max(self.resources.logical_processors - 1, 1)
        self.executor = ThreadPoolExecutor(
            max_workers=optimal_workers,
            thread_name_prefix="worker"
        )
        self.logger.info(f"Pool de threads inicializado com {optimal_workers} workers")

    # Outros métodos...

    def optimize_cpu_affinity(self) -> None:
        """Distribua a afinidade da CPU entre todos os núcleos disponíveis."""
        try:
            process = psutil.Process()
            # Use todos os processadores lógicos disponíveis
            available_cpus = list(range(self.resources.logical_processors))
            process.cpu_affinity(available_cpus)
            
            self.logger.info(
                f"Afinidade de CPU definida para uso {len(available_cpus)} processadores lógicos"
            )
        except Exception as e:
            self.logger.error(f"Falha ao definir a afinidade da CPU: {e}")

    def set_process_priority(self, high_priority: bool = True) -> None:
        """Defina a prioridade do processo com tratamento de erros."""
        try:
            process = psutil.Process()
            if high_priority:
                if os.name == 'nt':  # Windows
                    process.nice(psutil.HIGH_PRIORITY_CLASS)
                else:  # Linux/Unix
                    process.nice(-10 if os.geteuid() == 0 else 0)
            self.logger.info(f"Prioridade do processo definida como {'high' if high_priority else 'normal'}")
        except Exception as e:
            self.logger.error(f"Falha ao definir a prioridade do processo: {e}")

    def cleanup_chromium_processes(self) -> None:
        """Encerre processos do Chromium com segurança."""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'chromium' in proc.info['name'].lower():
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        self.logger.info(f"Processo Chromium encerrado: {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Erro ao limpar processos do Chromium: {e}")

    def graceful_shutdown(self, timeout: int = 5) -> None:
        """Realiza o desligamento gracioso de todos os recursos."""
        self.logger.info("Iniciando desligamento gracioso...")
        self.shutdown_event.set()

        try:
            # Desliga thread pool
            if self.executor:
                self.executor.shutdown(wait=True)
                time.sleep(timeout)
                
            # Reseta afinidade da CPU
            try:
                process = psutil.Process()
                process.cpu_affinity([0])
            except Exception as e:
                self.logger.warning(f"Falha ao resetar afinidade da CPU: {e}")

            # Limpa processos do Chromium
            self.cleanup_chromium_processes()

            # Reseta prioridade do processo
            self.set_process_priority(high_priority=False)

            self.logger.info("Desligamento gracioso completado com sucesso")
        except Exception as e:
            self.logger.error(f"Erro durante o desligamento: {e}")
            os._exit(1)