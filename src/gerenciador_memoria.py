import os
import ctypes
import logging
from typing import Optional
import subprocess

class GerenciadorMemoria:
    def __init__(self, logger):
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
                    
                    # Adiciona função de prioridade I/O diretamente
                    try:
                        # Define o tipo de retorno e argumentos para syscall
                        self.libc.syscall.argtypes = [ctypes.c_long, ctypes.c_int, ctypes.c_int]
                        self.libc.syscall.restype = ctypes.c_int
                        
                        # Adiciona método para set_io_priority
                        def set_io_priority():
                            IO_PRIO_CLASS_RT = 1
                            return self.libc.syscall(251, 1, 0)  # syscall para ioprio_set
                            
                        self.set_io_priority = set_io_priority
                        
                    except Exception as e:
                        self.logger.warning(f"[Sistema] Falha ao configurar função de I/O priority: {e}")
                    
                    break
                except OSError:
                    continue
                    
            if not self.libc:
                raise OSError("Não foi possível encontrar a biblioteca libc")
                
        except Exception as e:
            self.logger.error(f"[Sistema] Falha ao carregar libc: {e}")
            self.libc = None

    def configurar_memoria_locked(self) -> bool:
        """Configura o bloqueio de memória usando diferentes métodos e otimizações."""
        if not self.libc:
            self.logger.warning("[Sistema] libc não disponível para bloqueio de memória")
            return False

        try:
            # Primeiro aumenta limite de memória locked
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_MEMLOCK, (-1, -1))
            except Exception as e:
                self.logger.debug(f"[Sistema] Falha ao configurar limite de memória: {e}")

            # Configuração do mlockall com flags adicionais
            MCL_CURRENT = 1
            MCL_FUTURE = 2
            MCL_ONFAULT = 4  # Adiciona flag para page fault

            success = False
            if hasattr(self.libc, 'mlockall'):
                result = self.libc.mlockall(MCL_CURRENT | MCL_FUTURE | MCL_ONFAULT)
                if result == 0:
                    self.logger.info("[Sistema] Memória bloqueada com sucesso usando mlockall")
                    success = True
                else:
                    # Tenta sem MCL_ONFAULT caso falhe
                    result = self.libc.mlockall(MCL_CURRENT | MCL_FUTURE)
                    if result == 0:
                        self.logger.info("[Sistema] Memória bloqueada com sucesso (modo básico)")
                        success = True

            # Configurações adicionais se mlockall teve sucesso
            if success:
                # Configura swappiness
                if os.path.exists('/proc/sys/vm/swappiness'):
                    try:
                        cmd_prefix = [] if os.geteuid() == 0 else ['sudo']
                        subprocess.run(
                            cmd_prefix + ['sh', '-c', 'echo 0 > /proc/sys/vm/swappiness'],
                            check=True,
                            capture_output=True
                        )
                        self.logger.info("[Sistema] Swappiness configurado para 0")
                    except subprocess.CalledProcessError:
                        self.logger.warning("[Sistema] Não foi possível configurar swappiness (requer root)")

                # Configura prioridade de I/O usando syscall direta
                try:
                    if hasattr(self.libc, 'syscall'):
                        IOPRIO_CLASS_RT = 1
                        IOPRIO_WHO_PROCESS = 1
                        IOPRIO_SET = 289  # syscall number for ioprio_set
                        
                        ioprio = (IOPRIO_CLASS_RT << 13) | 0  # Prioridade mais alta
                        result = self.libc.syscall(
                            IOPRIO_SET,
                            IOPRIO_WHO_PROCESS,
                            os.getpid(),
                            ioprio
                        )
                        
                        if result == 0:
                            self.logger.info("[Sistema] Prioridade de I/O configurada via syscall")
                        else:
                            raise OSError("Falha na syscall de ioprio_set")
                            
                except Exception as e:
                    try:
                        cmd_prefix = [] if os.geteuid() == 0 else ['sudo']
                        subprocess.run(
                            cmd_prefix + ['ionice', '-c', '1', '-n', '0', str(os.getpid())],
                            check=True,
                            capture_output=True
                        )
                        self.logger.info("[Sistema] Prioridade de I/O configurada via ionice")
                    except subprocess.CalledProcessError as e:
                        self.logger.warning(f"[Sistema] Falha ao configurar prioridade de I/O: {e}")

                # Configurações adicionais de memória
                try:
                    # Desativa o THP (Transparent Huge Pages)
                    if os.path.exists('/sys/kernel/mm/transparent_hugepage/enabled'):
                        cmd_prefix = [] if os.geteuid() == 0 else ['sudo']
                        subprocess.run(
                            cmd_prefix + ['sh', '-c', 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'],
                            check=True,
                            capture_output=True
                        )
                        self.logger.info("[Sistema] THP desativado com sucesso")
                except Exception as e:
                    self.logger.debug(f"[Sistema] Falha ao configurar THP: {e}")

            return success

        except Exception as e:
            self.logger.error(f"[Sistema] Erro ao configurar memória: {e}")
            return False

    def limpar_configuracoes(self) -> None:
        """Limpa as configurações de memória ao encerrar."""
        try:
            # Determina se precisa usar sudo
            is_root = os.geteuid() == 0
            cmd_prefix = [] if is_root else ['sudo']

            # Limpa mlockall
            if self.libc and hasattr(self.libc, 'munlockall'):
                self.libc.munlockall()
                self.logger.info("[Sistema] Configurações de memória restauradas")

            # Restaura swappiness
            if os.path.exists('/proc/sys/vm/swappiness'):
                try:
                    subprocess.run(
                        cmd_prefix + ['sh', '-c', 'echo 60 > /proc/sys/vm/swappiness'],
                        check=True,
                        capture_output=True
                    )
                    self.logger.info("[Sistema] Swappiness restaurado para 60")
                except subprocess.CalledProcessError:
                    self.logger.warning("[Sistema] Falha ao restaurar swappiness")

            # Restaura THP se foi modificado
            if os.path.exists('/sys/kernel/mm/transparent_hugepage/enabled'):
                try:
                    subprocess.run(
                        cmd_prefix + ['sh', '-c', 'echo madvise > /sys/kernel/mm/transparent_hugepage/enabled'],
                        check=True,
                        capture_output=True
                    )
                    self.logger.info("[Sistema] THP restaurado para configuração padrão")
                except Exception:
                    self.logger.debug("[Sistema] Falha ao restaurar THP")

        except Exception as e:
            self.logger.error(f"[Sistema] Falha ao limpar configurações de memória: {e}")