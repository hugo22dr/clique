import os
import time
import fcntl
import logging
import ctypes
import subprocess
import psutil
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sync_constants import PRECISE_SYNC_WAIT, PRECISE_SYNC_SET_THREADS, SyncDevice

class LinuxPrecisionClickManager:
    def __init__(self, max_workers=None, logger=None):
        self.max_workers = max_workers or (os.cpu_count() - 2)  # Reserva 2 cores para sistema
        self.logger = logger or logging.getLogger(__name__)
        self.sync_device = SyncDevice()
        
        try:
            if self.max_workers:
                self.sync_device.set_threads(self.max_workers)
                
            # Configura núcleos disponíveis
            total_cores = os.cpu_count()
            self.ccx_size = 6  # Tamanho do CCX do Ryzen
            self.cores_disponíveis = list(range(2, total_cores))  # Reserva cores 0,1
                
        except Exception as e:
            self.logger.warning(f"Erro ao configurar número de threads: {e}")
            
        self._setup_hardware_sync()

    def _setup_hardware_sync(self):
        """Configura sincronização de hardware com otimização para Ryzen."""
        try:
            # Abre o dispositivo de sincronização
            self.sync_fd = os.open('/dev/precise_sync', os.O_RDWR)
            
            # Configura prioridade RT
            try:
                param = ctypes.c_int(99)
                SCHED_FIFO = 1
                libc = ctypes.CDLL('libc.so.6')
                if libc.sched_setscheduler(0, SCHED_FIFO, ctypes.byref(param)) != 0:
                    self.logger.warning("Falha ao configurar prioridade RT")
            except Exception as e:
                self.logger.warning(f"Erro ao configurar scheduler: {e}")

            # Otimização para Ryzen
            if self.max_workers:
                try:
                    total_cores = os.cpu_count()
                    cores_per_ccx = total_cores // 2  # Divide entre os CCXs
                    
                    # Distribui cores entre os CCXs
                    ccx1_cores = set(range(2, 2 + cores_per_ccx))
                    ccx2_cores = set(range(2 + cores_per_ccx, total_cores))
                    
                    # Define afinidade balanceada
                    cores_to_use = ccx1_cores | ccx2_cores
                    
                    if hasattr(os, 'sched_setaffinity'):
                        os.sched_setaffinity(0, cores_to_use)
                    self.logger.info(f"Afinidade de CPU otimizada: {len(cores_to_use)} cores ativos")
                except Exception as e:
                    self.logger.warning(f"Erro ao configurar CPU affinity: {e}")

            self.logger.info("Sincronização de hardware configurada com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar sincronização de hardware: {e}")
            raise RuntimeError(f"Falha na configuração de hardware: {e}")

    def prepare_browser(self, driver):
        """Prepara o navegador para cliques precisos."""
        try:
            driver.execute_script(
                """
                // Otimizações de performance
                if (window.gc) window.gc();
                performance.setResourceTimingBufferSize(0);
                performance.clearResourceTimings();

                // Desativa throttling
                window.__precisionMode = true;
                delete window.requestAnimationFrame;
                delete window.setTimeout;
                delete window.setInterval;

                // Manipulador de eventos otimizado
                const handler = e => {
                    e.stopPropagation();
                    e.preventDefault();
                    return true;
                };
                document.addEventListener('click', handler, {capture: true});
                """
            )
            self.logger.info(f"Browser {driver.session_id} preparado com otimizações")
        except Exception as e:
            self.logger.error(f"Erro ao preparar browser: {e}")

    def _ultra_precise_synchronized_click(self, driver, xpath):
        """Executa clique com sincronização precisa e limpeza de estado."""
        try:
            # Pre-localiza e valida elemento
            element = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            # Limpa estado do navegador antes do clique
            driver.execute_script("""
                // Limpa filas de eventos
                window.eventQueue = [];
                const originalAddEventListener = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                    if (!this.eventQueue) this.eventQueue = [];
                    this.eventQueue.push({type, listener, options});
                    return originalAddEventListener.call(this, type, listener, options);
                };

                // Força finalização de todas as animações
                const styles = document.createElement('style');
                styles.type = 'text/css';
                styles.innerHTML = '* { animation-duration: 0s !important; transition-duration: 0s !important; }';
                document.head.appendChild(styles);

                // Força sincronização do DOM
                document.documentElement.getBoundingClientRect();
                
                // Limpa timers pendentes
                const highestId = window.setTimeout(() => {}, 0);
                for (let i = 0; i < highestId; i++) {
                    window.clearTimeout(i);
                    window.clearInterval(i);
                }
                
                // Desativa throttling
                if (window.requestIdleCallback) {
                    window.cancelIdleCallback(window.requestIdleCallback(() => {}));
                }
                
                // Força GC
                if (window.gc) {
                    window.gc();
                }
                
                // Remove event listeners existentes do elemento
                const clone = arguments[0].cloneNode(true);
                arguments[0].parentNode.replaceChild(clone, arguments[0]);
                
                // Garante que o DOM está estável
                return new Promise(resolve => {
                    const observer = new MutationObserver((mutations, obs) => {
                        obs.disconnect();
                        resolve();
                    });
                    
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        characterData: true
                    });
                    
                    // Força uma verificação após 10ms
                    setTimeout(() => {
                        observer.disconnect();
                        resolve();
                    }, 10);
                });
            """, element)

            # Sincronização via kernel
            fcntl.ioctl(self.sync_fd, PRECISE_SYNC_WAIT)
            
            # Timestamp preciso pré-clique
            start_time = time.monotonic_ns()
            
            # Executa click com bypass de event listeners
            driver.execute_script("""
                const evt = new MouseEvent('click', {
                    bubbles: false,
                    cancelable: true,
                    view: window
                });
                
                // Bypass da fila de eventos
                Object.defineProperty(evt, '_bypassQueue', {
                    value: true,
                    writable: false
                });
                
                arguments[0].dispatchEvent(evt);
            """, element)
            
            # Timestamp pós-clique
            end_time = time.monotonic_ns()
            deviation = end_time - start_time

            self.logger.info(f"[Clique] Navegador {driver.session_id}: Desvio = {deviation/1000:.2f}μs")
            return True, deviation

        except Exception as e:
            self.logger.error(f"[Clique] Erro: {e}")
            return False, None

    def execute_synchronized_clicks(self, drivers, xpaths):
        if not drivers or not xpaths:
            return False

        # Pré-aquece todos os cores disponíveis
        with ThreadPoolExecutor(max_workers=len(self.cores_disponíveis)) as executor:
            list(executor.map(lambda _: None, range(1000000)))

        ccx_division = len(drivers) // 2
        with ThreadPoolExecutor(max_workers=len(drivers)) as executor:
            futures = []
            for idx, (driver, xpath) in enumerate(zip(drivers, xpaths)):
                # Distribui entre os CCXs
                ccx_id = idx // ccx_division
                core_start = 2 + (ccx_id * self.ccx_size)
                cores = set(range(core_start, core_start + self.ccx_size))
                
                try:
                    os.sched_setaffinity(0, cores)
                    self.logger.debug(f"Thread {idx} usando cores {cores}")
                except Exception as e:
                    self.logger.warning(f"Erro ao configurar cores {cores}: {e}")

                futures.append(
                    executor.submit(self._ultra_precise_synchronized_click, driver, xpath)
                )

            results = [future.result() for future in futures]

        success = all(r[0] for r in results if r)

        if success:
            deviations = [r[1] for r in results if r[1] is not None]
            if deviations:
                avg_deviation = sum(deviations) / len(deviations)
                max_deviation = max(deviations)
                self.logger.info(f"[Clique] Desvio médio: {avg_deviation/1000:.2f}μs")
                self.logger.info(f"[Clique] Desvio máximo: {max_deviation/1000:.2f}μs")

        return success

    def cleanup(self):
        """Limpa recursos e restaura configurações."""
        try:
            if hasattr(self, 'sync_fd'):
                os.close(self.sync_fd)
            if hasattr(self, 'sync_device'):
                del self.sync_device
            self.logger.info("Recursos de sincronização liberados")
        except Exception as e:
            self.logger.error(f"Erro ao limpar recursos: {e}")

    def __del__(self):
        """Destrutor que garante limpeza de recursos."""
        self.cleanup()