import os
import psutil
import logging
from typing import List, Set, Dict

class CPUManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.original_settings: Dict[str, str] = {}
        self.reserved_cores: Set[int] = set()

    def optimize_cpu_affinity(self, total_logical_processors: int) -> Set[int]:
        """Otimiza a distribuição de CPU para alto desempenho."""
        try:
            process = psutil.Process()
            
            # Manter cores 0-5 para sistema (primeiro CCX)
            system_ccx = set(range(6))
            available_cores = list(set(range(total_logical_processors)) - system_ccx)
            
            if available_cores:
                process.cpu_affinity(available_cores)
                self.reserved_cores = system_ccx
                self.logger.info(f"Afinidade de CPU ajustada: {len(available_cores)} threads disponíveis")
                return set(available_cores)
            else:
                return self._apply_fallback_cpu_settings()
                
        except Exception as e:
            self.logger.error(f"Falha ao otimizar afinidade da CPU: {e}")
            return self._apply_fallback_cpu_settings()

    def _apply_fallback_cpu_settings(self) -> Set[int]:
        """Aplica configurações mínimas de CPU em caso de falha."""
        try:
            process = psutil.Process()
            process.cpu_affinity([0])
            self.reserved_cores = {0}
            self.logger.warning("Configuração mínima de CPU aplicada.")
            return {0}
        except Exception as e:
            self.logger.error(f"Falha total na configuração de CPU: {e}")
            return set()

    def assign_cores_for_tasks(self, tasks: int, total_logical_processors: int) -> List[Set[int]]:
        """Divide os núcleos disponíveis respeitando CCXs."""
        ccx_size = 6  # Tamanho do CCX no Ryzen
        
        # Pula o primeiro CCX (sistema)
        available_cores = list(range(ccx_size, total_logical_processors))
        cores_per_task = max(2, len(available_cores) // tasks)
        
        assigned_cores = []
        for i in range(tasks):
            start_idx = i * cores_per_task
            end_idx = start_idx + cores_per_task
            task_cores = set(available_cores[start_idx:end_idx])
            assigned_cores.append(task_cores)
            
        self.logger.info(f"Núcleos alocados para tarefas: {assigned_cores}")
        return assigned_cores

    def configure_cpu_specific_settings(self):
        """Configura otimizações específicas para Intel/AMD."""
        cpu_vendor = "AMD" if "AMD" in os.uname().machine else "Intel"
        self.logger.info(f"Detectando arquitetura CPU: {cpu_vendor}")

        if cpu_vendor == "Intel":
            self._configure_intel_settings()
        elif cpu_vendor == "AMD":
            self._configure_amd_settings()

    def _configure_intel_settings(self):
        intel_pstate = '/sys/devices/system/cpu/intel_pstate/no_turbo'
        if os.path.exists(intel_pstate):
            try:
                with open(intel_pstate, 'r') as f:
                    self.original_settings['intel_turbo'] = f.read().strip()
                with open(intel_pstate, 'w') as f:
                    f.write('1')
                self.logger.info("Intel Turbo Boost desativado.")
            except Exception as e:
                self.logger.warning(f"Erro ao configurar Intel Turbo: {e}")

    def _configure_amd_settings(self):
        amd_pstate = '/sys/devices/system/cpu/cpufreq/boost'
        if os.path.exists(amd_pstate):
            try:
                with open(amd_pstate, 'r') as f:
                    self.original_settings['amd_boost'] = f.read().strip()
                with open(amd_pstate, 'w') as f:
                    f.write('0')
                self.logger.info("AMD Boost desativado.")
            except Exception as e:
                self.logger.warning(f"Erro ao configurar AMD Boost: {e}")

    def restore_cpu_settings(self, cpu_governors: Dict[int, str]):
        """Restaura configurações específicas de CPU."""
        # Restaura governors
        for cpu, governor in cpu_governors.items():
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
            if setting in self.original_settings and os.path.exists(path):
                try:
                    with open(path, 'w') as f:
                        f.write(self.original_settings[setting])
                except Exception as e:
                    self.logger.warning(f"Erro ao restaurar {setting}: {e}")