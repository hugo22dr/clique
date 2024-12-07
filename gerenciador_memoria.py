import os
import ctypes
import logging
from typing import Optional

class GerenciadorMemoria:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.libc: Optional[ctypes.CDLL] = None
        self._inicializar_libc()

    def _inicializar_libc(self) -> None:
        """Inicializa a biblioteca C com tratamento adequado de erros."""
        try:
            # Tenta carregar a libc em diferentes locais comuns
            libc_paths = [
                'libc.so.6',  # Linux padrão
                'libc.so',    # Algumas distribuições
                '/lib/x86_64-linux-gnu/libc.so.6',  # Debian/Ubuntu
                '/usr/lib64/libc.so.6'  # Red Hat/CentOS
            ]
            
            for path in libc_paths:
                try:
                    self.libc = ctypes.CDLL(path)
                    self.logger.info(f"[Sistema] libc carregada com sucesso de: {path}")
                    break
                except OSError:
                    continue
                    
            if not self.libc:
                raise OSError("Não foi possível encontrar a biblioteca libc")
                
        except Exception as e:
            self.logger.error(f"[Sistema] Falha ao carregar libc: {e}")
            self.libc = None

    def configurar_memoria_locked(self) -> bool:
        """
        Configura o bloqueio de memória usando diferentes métodos disponíveis.
        Retorna True se algum método foi bem-sucedido.
        """
        if not self.libc:
            self.logger.warning("[Sistema] libc não disponível para bloqueio de memória")
            return False

        success = False
        
        try:
            # Constantes para mlockall
            MCL_CURRENT = 1
            MCL_FUTURE = 2
            
            # Tenta usar mlockall via ctypes
            if hasattr(self.libc, 'mlockall'):
                result = self.libc.mlockall(MCL_CURRENT | MCL_FUTURE)
                if result == 0:
                    self.logger.info("[Sistema] Memória bloqueada com sucesso usando mlockall")
                    success = True
                else:
                    self.logger.warning("[Sistema] mlockall falhou, tentando métodos alternativos")
            
            # Método alternativo: configurar limite de memória locked
            if not success and os.geteuid() == 0:  # Verifica se é root
                try:
                    # Tenta aumentar limite de memória locked
                    import resource
                    resource.setrlimit(resource.RLIMIT_MEMLOCK, (-1, -1))
                    self.logger.info("[Sistema] Limite de memória locked aumentado com sucesso")
                    success = True
                except Exception as e:
                    self.logger.warning(f"[Sistema] Falha ao aumentar limite de memória locked: {e}")

            # Configurações adicionais de performance
            if success:
                # Desativa swap para o processo atual
                if os.path.exists('/proc/sys/vm/swappiness'):
                    try:
                        with open('/proc/sys/vm/swappiness', 'w') as f:
                            f.write('0')
                        self.logger.info("[Sistema] Swappiness configurado para 0")
                    except PermissionError:
                        self.logger.warning("[Sistema] Não foi possível configurar swappiness (requer root)")

                # Configura prioridade de I/O
                try:
                    import subprocess
                    subprocess.run(['ionice', '-c', '1', '-n', '0', str(os.getpid())], 
                                check=True, 
                                capture_output=True)
                    self.logger.info("[Sistema] Prioridade de I/O configurada com sucesso")
                except Exception as e:
                    self.logger.warning(f"[Sistema] Falha ao configurar prioridade de I/O: {e}")

        except Exception as e:
            self.logger.error(f"[Sistema] Erro ao configurar memória: {e}")
            success = False

        return success

    def limpar_configuracoes(self) -> None:
        """Limpa as configurações de memória ao encerrar."""
        try:
            if self.libc and hasattr(self.libc, 'munlockall'):
                self.libc.munlockall()
                self.logger.info("[Sistema] Configurações de memória restauradas")
                
            # Restaura swappiness se foi modificado
            if os.path.exists('/proc/sys/vm/swappiness'):
                try:
                    with open('/proc/sys/vm/swappiness', 'w') as f:
                        f.write('60')  # Valor padrão comum
                except PermissionError:
                    pass
                
        except Exception as e:
            self.logger.warning(f"[Sistema] Falha ao limpar configurações de memória: {e}")