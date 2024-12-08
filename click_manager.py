import os
import time
import fcntl
import logging
import ctypes
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sync_constants import PRECISE_SYNC_WAIT, PRECISE_SYNC_SET_THREADS, SyncDevice

class PreciseBrowserSync:
    def __init__(self, logger=None, sync_device=None):
        self.logger = logger or logging.getLogger(__name__)
        self.sync_device = sync_device or SyncDevice()
        
    def prepare_browser(self, driver):
        try:
            driver.execute_script("""
                // Desativa throttling e GC
                if (window.gc) window.gc();
                performance.setResourceTimingBufferSize(0);
                performance.clearResourceTimings();
                
                // Otimizações de evento
                const handler = e => {
                    e.stopPropagation();
                    e.preventDefault();
                    return true;
                };
                document.addEventListener('click', handler, {capture: true});
            """)
            self.logger.info(f"Browser {driver.session_id} preparado com otimizações")
        except Exception as e:
            self.logger.error(f"Erro ao preparar browser: {e}")

    def sync_click(self, drivers, elements):
        try:
            # Pré-carrega elementos
            for element in elements:
                element.get_attribute('id')
            
            # Sincronização precisa usando o dispositivo
            start_time = time.monotonic_ns()
            self.sync_device.wait_sync()
            
            # Executa clicks
            for driver, element in zip(drivers, elements):
                driver.execute_script("""
                    arguments[0].click();
                    performance.mark('click-time');
                """, element)
                
            end_time = time.monotonic_ns()
            self.logger.info(f"Clicks executados com desvio de {(end_time - start_time)/1000:.2f}μs")
            
            return True
        except Exception as e:
            self.logger.error(f"Erro na sincronização: {e}")
            return False

    def __del__(self):
        if hasattr(self, 'sync_device'):
            del self.sync_device

class LinuxPrecisionClickManager:
    def __init__(self, max_workers=None, logger=None, sync_device=None):
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
        self.sync_manager = PreciseBrowserSync(
            logger=self.logger, 
            sync_device=sync_device
        )
        self._setup_hardware_sync()

    def _setup_hardware_sync(self):
        try:
            # Configurações de sistema
            os.system("echo 2-3 > /sys/devices/system/cpu/isolated")
            os.system("echo 0 > /sys/devices/system/cpu/cpu0/cpuidle/state1/disable")
            
            # Lock memória
            try:
                import resource
                resource.mlockall(resource.MCL_CURRENT | resource.MCL_FUTURE)
            except Exception:
                self.logger.warning("Não foi possível fazer lock da memória")
                
        except Exception as e:
            self.logger.warning(f"Erro ao configurar otimizações: {e}")

    def _ultra_precise_synchronized_click(self, driver, xpath):
        try:
            # Localiza elemento
            element = driver.find_element(By.XPATH, xpath)
            
            # Prepara browser
            self.sync_manager.prepare_browser(driver)
            
            return element
                
        except Exception as e:
            self.logger.error(f"[Clique] Erro: {e}")
            return None

    def execute_synchronized_clicks(self, drivers, xpaths):
        if not drivers or not xpaths:
            return False
                
        # Prepara elementos
        elements = []
        for driver, xpath in zip(drivers, xpaths):
            element = self._ultra_precise_synchronized_click(driver, xpath)
            if element is None:
                return False
            elements.append(element)
        
        # Executa clicks sincronizados
        success = self.sync_manager.sync_click(drivers, elements)
        
        if success:
            self.logger.info("[Clique] Todos os cliques foram bem-sucedidos.")
        
        return success

    def cleanup(self):
        """Limpa recursos alocados."""
        if hasattr(self, 'sync_manager'):
            del self.sync_manager