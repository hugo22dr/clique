import os
import psutil
import ctypes
import logging
from typing import Dict

class MemoryManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.libc = None
        self.original_settings: Dict[str, str] = {}
        self._load_libc()

    def _load_libc(self):
        """Carrega a libc uma única vez durante a inicialização."""
        try:
            self.libc = ctypes.CDLL('libc.so.6')
            self.logger.info("[Sistema] libc carregada com sucesso de: libc.so.6.")
        except Exception as e:
            self.logger.error(f"[Sistema] Erro ao carregar libc: {e}")
            self.libc = None

    def memory_lock(self) -> bool:
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

    def configure_memory_settings(self) -> None:
        """Configura parâmetros específicos de memória."""
        settings = {
            'swappiness': ('/proc/sys/vm/swappiness', '10'),
            'thp': ('/sys/kernel/mm/transparent_hugepage/enabled', 'never')
        }

        for setting, (path, value) in settings.items():
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        self.original_settings[setting] = f.read().strip()
                    with open(path, 'w') as f:
                        f.write(value)
                    self.logger.info(f"{setting.upper()} configurado com sucesso.")
                except Exception as e:
                    self.logger.warning(f"Erro ao configurar {setting}: {e}")

    def restore_memory_settings(self) -> None:
        """Restaura configurações específicas de memória."""
        memory_settings = {
            'swappiness': '/proc/sys/vm/swappiness',
            'thp': '/sys/kernel/mm/transparent_hugepage/enabled'
        }

        for setting, path in memory_settings.items():
            if setting in self.original_settings and os.path.exists(path):
                try:
                    with open(path, 'w') as f:
                        f.write(self.original_settings[setting])
                    self.logger.info(f"{setting.upper()} restaurado para configuração original")
                except Exception as e:
                    self.logger.warning(f"Erro ao restaurar {setting}: {e}")