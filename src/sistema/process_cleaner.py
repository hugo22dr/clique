import psutil
import logging
from typing import List, Set

class ProcessCleaner:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.chrome_patterns = [
            'chrome', 'chromium', 'chromium-browser', 'google-chrome',
            'chrome.exe', 'chromium.exe', 'google-chrome.exe',
            'chrome-sandbox', 'chrome-crashpad'
        ]

    def cleanup_chromium_processes(self) -> Set[int]:
        """
        Encerra processos do Chrome/Chromium com detecção aprimorada e logging detalhado.
        """
        killed_pids = set()
        process_tree = {}

        try:
            # Mapear a árvore de processos
            for proc in psutil.process_iter(['pid', 'name', 'ppid']):
                try:
                    proc_info = proc.info
                    process_tree[proc_info['pid']] = {
                        'name': proc_info['name'].lower(),
                        'ppid': proc_info['ppid']
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Identificar processos Chrome/Chromium e seus filhos
            chrome_processes = self._find_chrome_processes(process_tree)

            # Encerrar processos de forma ordenada
            for pid in sorted(set(chrome_processes), reverse=True):
                if pid not in killed_pids:
                    killed_pids.update(self._terminate_process(pid))

            # Verificação final
            remaining_chrome = self._check_remaining_chrome_processes()

            if remaining_chrome:
                self.logger.warning(f"Processos Chrome/Chromium ainda ativos: {remaining_chrome}")
            else:
                self.logger.info(f"Limpeza concluída. Total de processos encerrados: {len(killed_pids)}")

        except Exception as e:
            self.logger.error(f"Erro durante limpeza de processos Chrome/Chromium: {str(e)}")

        return killed_pids

    def _find_chrome_processes(self, process_tree: dict) -> List[int]:
        """Identifica processos Chrome/Chromium e seus filhos."""
        chrome_processes = []
        for pid, info in process_tree.items():
            if any(pattern in info['name'] for pattern in self.chrome_patterns):
                chrome_processes.append(pid)
                # Adicionar processos filhos
                for other_pid, other_info in process_tree.items():
                    if other_info['ppid'] == pid:
                        chrome_processes.append(other_pid)
        return chrome_processes

    def _terminate_process(self, pid: int) -> Set[int]:
        """Tenta encerrar um processo de forma graciosa ou forçada."""
        killed_pids = set()
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name().lower()
            
            self.logger.info(f"Tentando encerrar processo: {pid} ({proc_name})")
            
            proc.terminate()
            try:
                proc.wait(timeout=3)
                killed_pids.add(pid)
                self.logger.info(f"Processo {pid} ({proc_name}) encerrado com sucesso via terminate()")
                return killed_pids
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
        
        return killed_pids

    def _check_remaining_chrome_processes(self) -> List[int]:
        """Verifica se existem processos Chrome/Chromium ainda ativos."""
        remaining_chrome = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if any(pattern in proc.info['name'].lower() for pattern in self.chrome_patterns):
                    remaining_chrome.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return remaining_chrome
    