import time
import logging
import click_sync
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LinuxPrecisionClickManager:
    def __init__(self, max_workers=None, logger=None):
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
        click_sync.setup_sync(max_workers)

    def _stabilize_element(self, driver, element):
        """Estabiliza o estado do elemento antes do clique"""
        js_stabilize = """
            arguments[0].blur();  // Remove foco
            let rect = arguments[0].getBoundingClientRect();
            arguments[0].scrollIntoView({
                behavior: 'instant',
                block: 'center'
            });
            // Força recálculo do layout
            void arguments[0].offsetHeight;
            // Desativa eventos temporariamente
            let oldClick = arguments[0].onclick;
            arguments[0].onclick = null;
            return {
                ready: true,
                x: rect.left + (rect.width / 2),
                y: rect.top + (rect.height / 2)
            };
        """
        return driver.execute_script(js_stabilize, element)

    def _prepare_click(self, driver, element):
        """Prepara o evento de clique otimizado"""
        js_prepare = """
            // Cria evento otimizado
            window.__preciseClick = function(el, x, y) {
                const events = ['mousedown', 'mouseup', 'click'];
                events.forEach(type => {
                    const evt = new MouseEvent(type, {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        detail: 1,
                        screenX: x,
                        screenY: y,
                        clientX: x,
                        clientY: y
                    });
                    el.dispatchEvent(evt);
                });
            };
        """
        driver.execute_script(js_prepare)

    def _ultra_precise_synchronized_click(self, driver, xpath):
        try:
            # 1. Pre-localiza elemento com retry
            for _ in range(3):
                try:
                    element = WebDriverWait(driver, 0.1).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    break
                except:
                    continue
            else:
                raise Exception("Elemento não encontrado")

            # 2. Estabiliza estado
            element_state = self._stabilize_element(driver, element)
            if not element_state['ready']:
                raise Exception("Elemento não estabilizou")

            # 3. Prepara evento de clique
            self._prepare_click(driver, element)
            
            # 4. Aguarda sincronização tripla
            target_ns = click_sync.wait_for_click()
            
            # 5. Executa clique preciso
            click_js = f"""
                window.__preciseClick(
                    arguments[0], 
                    {element_state['x']}, 
                    {element_state['y']}
                );
            """
            driver.execute_script(click_js, element)
            
            actual_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
            deviation = abs(actual_ns - target_ns)
            
            self.logger.info(f"[Clique] Navegador {driver.session_id}: Desvio = {deviation:.2f}ns")
            return True, deviation
            
        except Exception as e:
            self.logger.error(f"[Clique] Erro: {e}")
            return False, None

    def execute_synchronized_clicks(self, drivers, xpaths):
        if not drivers or not xpaths:
            return False
            
        with ThreadPoolExecutor(max_workers=len(drivers)) as executor:
            futures = [
                executor.submit(self._ultra_precise_synchronized_click, driver, xpath)
                for driver, xpath in zip(drivers, xpaths)
            ]
            results = [future.result() for future in futures]
        
        return all(r[0] for r in results if r)