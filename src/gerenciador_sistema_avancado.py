from concurrent.futures import ThreadPoolExecutor
import os
import psutil
import ctypes
import signal
import time
import subprocess
from typing import List, Optional, Dict, Set
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
        self._original_settings: Dict[str, str] = {}
        self.libc = None
        self.cpu_governors: Dict[int, str] = {}
        self.resources = self._get_system_resources()
        self.shutdown_event = Event()
        self.executor = None
        self.reserved_cores: Set[int] = set()

        # Configuração inicial
        self._load_libc()
        self._setup_signal_handlers()
        self._initialize_thread_pool()

    def _setup_signal_handlers(self):
        """Configura handlers para todos os sinais relevantes."""
        signals = [
            signal.SIGTERM, signal.SIGINT, signal.SIGQUIT,
            signal.SIGSEGV, signal.SIGABRT
        ]
        for sig in signals:
            try:
                signal.signal(sig, self._handle_signal)
            except Exception as e:
                self.logger.warning(f"Não foi possível configurar handler para sinal {sig}: {e}")
        self.logger.info("Manipuladores de sinais registrados com sucesso.")

    def _handle_signal(self, signum, frame):
        """Handler central para todos os sinais."""
        if self.shutdown_event.is_set():
            return
        self.logger.info(f"Sinal {signum} recebido. Iniciando desligamento seguro...")
        self.shutdown_event.set()
        self.graceful_shutdown()

    def optimize_cpu_affinity(self) -> None:
        """Otimiza a distribuição de CPU para alto desempenho."""
        try:
            process = psutil.Process()
            total_logical = self.resources.logical_processors  # 24 threads

            # Manter cores 0-5 para sistema (primeiro CCX)
            system_ccx = set(range(6))  # Primeiro CCX para sistema
            available_cores = list(set(range(total_logical)) - system_ccx)
            
            # Usa todos os cores restantes
            cores_to_use = available_cores
            
            if cores_to_use:
                process.cpu_affinity(cores_to_use)
                self.reserved_cores = system_ccx  # Salva os cores reservados
                self.logger.info(f"Afinidade de CPU ajustada: {len(cores_to_use)} threads disponíveis")
            else:
                self._apply_fallback_cpu_settings()
                
        except Exception as e:
            self.logger.error(f"Falha ao otimizar afinidade da CPU: {e}")
            self._apply_fallback_cpu_settings()

    def assign_cores_for_tasks(self, tasks: int) -> List[Set[int]]:
        """Divide os núcleos disponíveis respeitando CCXs."""
        ccx_size = 6  # Tamanho do CCX no Ryzen
        total_logical = self.resources.logical_processors
        
        # Pula o primeiro CCX (sistema)
        available_cores = list(range(ccx_size, total_logical))
        cores_per_task = max(2, len(available_cores) // tasks)
        
        assigned_cores = []
        for i in range(tasks):
            start_idx = i * cores_per_task
            end_idx = start_idx + cores_per_task
            task_cores = set(available_cores[start_idx:end_idx])
            assigned_cores.append(task_cores)
            
        self.logger.info(f"Núcleos alocados para tarefas: {assigned_cores}")
        return assigned_cores

    def _apply_fallback_cpu_settings(self):
        """Aplica configurações mínimas de CPU em caso de falha."""
        try:
            process = psutil.Process()
            process.cpu_affinity([0])  # Fallback para núcleo 0
            self.reserved_cores = {0}
            self.logger.warning("Configuração mínima de CPU aplicada.")
        except Exception as e:
            self.logger.error(f"Falha total na configuração de CPU: {e}")

    def _configure_cpu_specific_settings(self):
        """Configura otimizações específicas para Intel/AMD."""
        cpu_vendor = "AMD" if "AMD" in os.uname().machine else "Intel"
        self.logger.info(f"Detectando arquitetura CPU: {cpu_vendor}")

        if cpu_vendor == "Intel":
            intel_pstate = '/sys/devices/system/cpu/intel_pstate/no_turbo'
            if os.path.exists(intel_pstate):
                try:
                    with open(intel_pstate, 'r') as f:
                        self._original_settings['intel_turbo'] = f.read().strip()
                    with open(intel_pstate, 'w') as f:
                        f.write('1')
                    self.logger.info("Intel Turbo Boost desativado.")
                except Exception as e:
                    self.logger.warning(f"Erro ao configurar Intel Turbo: {e}")

        elif cpu_vendor == "AMD":
            amd_pstate = '/sys/devices/system/cpu/cpufreq/boost'
            if os.path.exists(amd_pstate):
                try:
                    with open(amd_pstate, 'r') as f:
                        self._original_settings['amd_boost'] = f.read().strip()
                    with open(amd_pstate, 'w') as f:
                        f.write('0')
                    self.logger.info("AMD Boost desativado.")
                except Exception as e:
                    self.logger.warning(f"Erro ao configurar AMD Boost: {e}")

    def _load_libc(self):
        """Carrega a libc uma única vez durante a inicialização."""
        try:
            self.libc = ctypes.CDLL('libc.so.6')
            self.MCL_CURRENT = 1
            self.MCL_FUTURE = 2
            self.logger.info("[Sistema] libc carregada com sucesso de: libc.so.6.")
        except Exception as e:
            self.logger.error(f"[Sistema] Erro ao carregar libc: {e}")
            self.libc = None

    def _memory_lock(self) -> bool:
        """Tentativa de bloqueio de memória com fallback."""
        if not self.libc:
            self.logger.warning("libc não disponível para lock de memória.")
            return False

        try:
            if hasattr(self.libc, 'mlock'):
                process = psutil.Process()
                mem_info = process.memory_info()
                result = self.libc.mlock(0, mem_info.rss)
                if result == 0:
                    self.logger.info("Memória bloqueada com sucesso usando mlock.")
                    return True
            # Fallback: Reduz swappiness como alternativa
            if os.path.exists('/proc/sys/vm/swappiness'):
                with open('/proc/sys/vm/swappiness', 'w') as f:
                    f.write('10')
                self.logger.info("Swappiness reduzida como alternativa ao lock de memória.")
            return False
        except Exception as e:
            self.logger.warning(f"Falha no lock de memória: {e}")
            return False

    def _get_system_resources(self) -> SystemResources:
        """Coleta informações sobre os recursos do sistema."""
        return SystemResources(
            total_cores=psutil.cpu_count(logical=False),
            logical_processors=psutil.cpu_count(logical=True),
            available_memory=psutil.virtual_memory().available,
            process_id=os.getpid()
        )

    def _initialize_thread_pool(self, tasks: int = 4) -> None:
        """Inicializa o pool de threads com otimização."""
        try:
            core_assignments = self.assign_cores_for_tasks(tasks)
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

    def set_process_priority(self, priority: int = -10) -> None:
        """Define a prioridade do processo usando 'nice'."""
        try:
            pid = os.getpid()
            os.nice(priority)
            self.logger.info(f"Prioridade do processo configurada para {priority} com sucesso.")
        except PermissionError:
            self.logger.warning("Permissão negada ao configurar prioridade de processo. Tente rodar com sudo.")
        except Exception as e:
            self.logger.error(f"Erro ao configurar prioridade do processo: {e}")

    def optimize_memory_settings(self) -> None:
        """Otimiza configurações de memória para melhor performance."""
        try:
            self._memory_lock()
            self._configure_memory_settings()
        except Exception as e:
            self.logger.error(f"Erro ao otimizar configurações de memória: {e}")

    def _configure_memory_settings(self) -> None:
        """Configura parâmetros específicos de memória."""
        settings = {
            'swappiness': ('/proc/sys/vm/swappiness', '10'),
            'thp': ('/sys/kernel/mm/transparent_hugepage/enabled', 'never')
        }

        for setting, (path, value) in settings.items():
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        self._original_settings[setting] = f.read().strip()
                    with open(path, 'w') as f:
                        f.write(value)
                    self.logger.info(f"{setting.upper()} configurado com sucesso.")
                except Exception as e:
                    self.logger.warning(f"Erro ao configurar {setting}: {e}")

    def cleanup_chromium_processes(self) -> None:
        """
        Encerra processos do Chrome/Chromium com detecção aprimorada e logging detalhado.
        Inclui verificação de subprocessos e múltiplos padrões de nome.
        """
        chrome_patterns = [
            'chrome', 'chromium', 'chromium-browser', 'google-chrome',
            'chrome.exe', 'chromium.exe', 'google-chrome.exe',
            'chrome-sandbox', 'chrome-crashpad'
        ]
        killed_pids = set()
        process_tree = {}

        try:
            # Primeiro passo: Mapear a árvore de processos
            for proc in psutil.process_iter(['pid', 'name', 'ppid']):
                try:
                    proc_info = proc.info
                    process_tree[proc_info['pid']] = {
                        'name': proc_info['name'].lower(),
                        'ppid': proc_info['ppid']
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Segundo passo: Identificar processos Chrome/Chromium e seus filhos
            chrome_processes = []
            for pid, info in process_tree.items():
                if any(pattern in info['name'] for pattern in chrome_patterns):
                    chrome_processes.append(pid)
                    # Adicionar processos filhos
                    for other_pid, other_info in process_tree.items():
                        if other_info['ppid'] == pid:
                            chrome_processes.append(other_pid)

            # Terceiro passo: Encerrar processos de forma ordenada
            for pid in sorted(set(chrome_processes), reverse=True):
                if pid not in killed_pids:
                    try:
                        proc = psutil.Process(pid)
                        proc_name = proc.name().lower()
                        
                        self.logger.info(f"Tentando encerrar processo: {pid} ({proc_name})")
                        
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                            killed_pids.add(pid)
                            self.logger.info(f"Processo {pid} ({proc_name}) encerrado com sucesso via terminate()")
                            continue
                        except psutil.TimeoutExpired:
                            self.logger.warning(f"Timeout ao aguardar término do processo {pid}, tentando kill()")
                        
                        proc.kill()
                        proc.wait(timeout=1)
                        killed_pids.add(pid)
                        self.logger.info(f"Processo {pid} ({proc_name}) encerrado com kill()")
                        
                    except psutil.NoSuchProcess:
                        self.logger.info(f"Processo {pid} já não existe")
                    except psutil.AccessDenied:
                        self.logger.warning(f"Acesso negado ao processo {pid}")
                    except Exception as e:
                        self.logger.error(f"Erro ao encerrar processo {pid}: {str(e)}")

            # Verificação final
            remaining_chrome = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if any(pattern in proc.info['name'].lower() for pattern in chrome_patterns):
                        remaining_chrome.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if remaining_chrome:
                self.logger.warning(f"Processos Chrome/Chromium ainda ativos: {remaining_chrome}")
            else:
                self.logger.info(f"Limpeza concluída. Total de processos encerrados: {len(killed_pids)}")

        except Exception as e:
            self.logger.error(f"Erro durante limpeza de processos Chrome/Chromium: {str(e)}")

    def restore_system_settings(self) -> None:
        """Restaura todas as configurações do sistema ao estado original."""
        try:
            self._restore_cpu_settings()
            self._restore_memory_settings()
            self.logger.info("Configurações do sistema restauradas com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao restaurar configurações do sistema: {e}")

    def _restore_cpu_settings(self) -> None:
        """Restaura configurações específicas de CPU."""
        # Restaura governors
        for cpu, governor in self.cpu_governors.items():
            governor_path = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
            if os.path.exists(governor_path):
                try:
                    with open(governor_path, 'w') as f:
                        f.write(governor)
                except Exception as e:
                    self.logger.warning(f"Erro ao restaurar governor CPU {cpu}: {e}")

        # Restaura Intel/AMD boost
        cpu_settings = {
            'intel_turbo': '/sys/devices/system/cpu/intel_pstate/no_turbo',
            'amd_boost': '/sys/devices/system/cpu/cpufreq/boost'
        }

        for setting, path in cpu_settings.items():
            if setting in self._original_settings and os.path.exists(path):
                try:
                    with open(path, 'w') as f:
                        f.write(self._original_settings[setting])
                except Exception as e:
                    self.logger.warning(f"Erro ao restaurar {setting}: {e}")

    def _restore_memory_settings(self) -> None:
        """Restaura configurações específicas de memória."""
        memory_settings = {
            'swappiness': '/proc/sys/vm/swappiness',
            'thp': '/sys/kernel/mm/transparent_hugepage/enabled'
        }

        for setting, path in memory_settings.items():
            if setting in self._original_settings and os.path.exists(path):
                try:
                    with open(path, 'w') as f:
                        f.write(self._original_settings[setting])
                    self.logger.info(f"{setting.upper()} restaurado para configuração original")
                except Exception as e:
                    self.logger.warning(f"Erro ao restaurar {setting}: {e}")

    def graceful_shutdown(self, timeout: int = 5) -> None:
        """Realiza desligamento gracioso com garantias extras."""
        if self.shutdown_event.is_set():
            return

        self.shutdown_event.set()
        self.logger.info("Iniciando procedimento de desligamento gracioso...")

        try:
            # Restaura configurações de CPU imediatamente
            process = psutil.Process()
            try:
                # Libera todos os cores antes de continuar
                all_cores = list(range(psutil.cpu_count()))
                process.cpu_affinity(all_cores)
            except Exception as e:
                self.logger.error(f"Erro ao restaurar afinidade CPU: {e}")

            # Força término de processos Chrome primeiro
            self.cleanup_chromium_processes()

            # Desliga thread pool
            if self.executor:
                self.executor.shutdown(wait=False)

            # Restaura configurações do sistema
            self.restore_system_settings()

            self.logger.info("Desligamento gracioso completado")

        except Exception as e:
            self.logger.error(f"Erro durante shutdown: {e}")
        finally:
            # Força saída do programa
            os._exit(0)
