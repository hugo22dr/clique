import ctypes
import fcntl
import os
from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constantes alinhadas com o kernel
CLICK_SYNC_MAGIC = ord('k')
CLICK_BUFFER_SIZE = 256
MAX_THREADS = 16

class ThreadCount(ctypes.Structure):
    """Estrutura para contagem de threads, alinhada com o kernel."""
    _pack_ = 1
    _fields_ = [
        ('count', ctypes.c_int)
    ]

class ClickData(ctypes.Structure):
    """Estrutura alinhada para dados do clique."""
    _pack_ = 1
    _fields_ = [
        ('element_ptr', ctypes.c_void_p),
        ('click_time', ctypes.c_uint64),
        ('driver_id', ctypes.c_int),
        ('xpath', ctypes.c_char * CLICK_BUFFER_SIZE),
        ('status', ctypes.c_int),
        ('actual_click_time', ctypes.c_uint64)
    ]

class SyncClickCmd(ctypes.Structure):
    """Comando de sincronização alinhado."""
    _pack_ = 1
    _fields_ = [
        ('clicks', ClickData * MAX_THREADS),
        ('num_clicks', ctypes.c_int),
        ('sync_time', ctypes.c_uint64),
        ('completed_clicks', ctypes.c_int),
        ('cmd_lock', ctypes.c_uint32)
    ]

class AtomicClickExecutor:
    def __init__(self, logger):
        self.logger = logger
        self.device_fd = None
        self.element_cache = {}
        
        # Definição correta dos comandos IOCTL
        self.CLICK_SYNC_SET_THREADS = self._IOW(CLICK_SYNC_MAGIC, 1, ThreadCount)
        self.CLICK_SYNC_WAIT = self._IOW(CLICK_SYNC_MAGIC, 2, ctypes.c_ulong)
        self.CLICK_SYNC_ATOMIC = self._IOW(CLICK_SYNC_MAGIC, 3, SyncClickCmd)
        
        self._initialize_device()

    def _IOW(self, type_num: int, nr: int, struct_type) -> int:
        """Recria macro _IOW do kernel usando tipos ctypes."""
        if isinstance(struct_type, str):
            size = ctypes.sizeof(getattr(ctypes, 'c_' + struct_type))
        else:
            size = ctypes.sizeof(struct_type)
            
        IOC_WRITE = 1
        IOC_SIZEBITS = 14
        IOC_SIZESHIFT = 16
        
        return (IOC_WRITE << 30) | (size << IOC_SIZESHIFT) | (type_num << 8) | nr

    def _initialize_device(self) -> None:
        """Inicializa dispositivo de sincronização."""
        try:
            self.device_fd = os.open("/dev/precise_sync", os.O_RDWR)
            self.logger.info("Dispositivo de sincronização inicializado")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar dispositivo: {e}")
            raise

    def _set_threads(self, num_threads: int) -> bool:
        """Configura número de threads usando estrutura alinhada."""
        if not (0 < num_threads <= MAX_THREADS):
            return False

        try:
            # Cria e inicializa estrutura ThreadCount
            tc = ThreadCount()
            tc.count = num_threads
            
            # Log para debug
            self.logger.debug(f"Enviando ThreadCount: size={ctypes.sizeof(tc)}, count={tc.count}")
            
            result = fcntl.ioctl(self.device_fd, self.CLICK_SYNC_SET_THREADS, tc)
            return result >= 0
        except Exception as e:
            self.logger.error(f"Erro ao configurar threads: {e}")
            return False

    def execute_synchronized_clicks(self, drivers: List[WebDriver], xpaths: List[str]) -> bool:
        """Executa cliques sincronizados usando estruturas alinhadas."""
        if len(drivers) != len(xpaths) or len(drivers) > MAX_THREADS:
            return False

        try:
            # Configura threads
            if not self._set_threads(len(drivers)):
                return False

            # Prepara comando
            cmd = SyncClickCmd()
            cmd.num_clicks = len(drivers)
            cmd.sync_time = 0
            cmd.completed_clicks = 0
            cmd.cmd_lock = 0  # Inicializa o lock

            # Prepara elementos
            for i, (driver, xpath) in enumerate(zip(drivers, xpaths)):
                try:
                    # Localiza elemento
                    element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    
                    # Otimiza renderização
                    driver.execute_script("""
                        const style = document.createElement('style');
                        style.textContent = '*{animation:none!important;transition:none!important}';
                        document.head.appendChild(style);
                        arguments[0].scrollIntoView(true);
                    """, element)

                    # Configura dados do clique
                    click = cmd.clicks[i]
                    click.element_ptr = id(element)
                    click.driver_id = i
                    
                    encoded_xpath = xpath.encode('utf-8')[:CLICK_BUFFER_SIZE-1]
                    click.xpath = encoded_xpath + b'\0' * (CLICK_BUFFER_SIZE - len(encoded_xpath))
                    
                    click.status = 0  # CLICK_PENDING
                    click.click_time = 0
                    click.actual_click_time = 0

                    # Cache do elemento
                    self.element_cache[f"{i}:{xpath}"] = element
                    self.logger.debug(f"Preparado clique {i}: xpath={xpath[:32]}...")

                except Exception as e:
                    self.logger.error(f"Erro ao preparar elemento {i}: {e}")
                    return False

            # Debug log
            self.logger.debug(f"Enviando SyncClickCmd: size={ctypes.sizeof(cmd)}, num_clicks={cmd.num_clicks}")

            # Executa sincronização
            try:
                result = fcntl.ioctl(self.device_fd, self.CLICK_SYNC_ATOMIC, cmd)
                if result < 0:
                    raise OSError(f"IOCTL falhou com código {result}")
            except Exception as e:
                self.logger.error(f"Erro na sincronização atômica: {e}")
                return False

            # Executa cliques usando elemento em cache
            for i, (driver, xpath) in enumerate(zip(drivers, xpaths)):
                try:
                    element = self.element_cache[f"{i}:{xpath}"]
                    driver.execute_script("arguments[0].click();", element)
                except Exception as e:
                    self.logger.error(f"Erro ao clicar no elemento {i}: {e}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Erro durante execução sincronizada: {e}")
            return False
            
        finally:
            self.element_cache.clear()

    def cleanup(self) -> None:
        """Limpa recursos."""
        if self.device_fd is not None:
            try:
                os.close(self.device_fd)
            except:
                pass
            self.device_fd = None
        self.element_cache.clear()