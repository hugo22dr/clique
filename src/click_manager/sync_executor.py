import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

class SynchronizedClickExecutor:
    def __init__(self, logger, timestamp_logger, max_workers=None):
        self.logger = logger
        self.timestamp_logger = timestamp_logger
        self.max_workers = max_workers or max(2, os.cpu_count() - 2)

    def localizar_elemento_resiliente(self, driver, xpath, tentativas=3):
        """Localiza elemento com tentativas resilientes."""
        for _ in range(tentativas):
            try:
                elemento = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                return elemento
            except StaleElementReferenceException:
                self.logger.warning("🔄 Tentando localizar elemento novamente...")
        return None

    def execute_synchronized_click(self, driver, xpath, barrier):
        """Executa clique sincronizado com captura de timestamps."""
        try:
            self.timestamp_logger.log_timestamp('Pre-Localization', id(driver))

            # Localização resiliente do elemento
            self.logger.info(f"🔍 Localizando elemento em {id(driver)}")
            elemento = self.localizar_elemento_resiliente(driver, xpath)
            if not elemento:
                raise Exception("Elemento não encontrado ou stale")

            self.logger.info("✨ Elemento encontrado!")

            # Scroll otimizado
            self.logger.info("📜 Executando scroll...")
            driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
            time.sleep(0.01)  # Pequeno delay mínimo
            self.logger.info("👀 Elemento visível no centro da tela")

            self.timestamp_logger.log_timestamp('Post-Localization', id(driver))
            self.logger.info("🚦 Aguardando na barreira de sincronização...")

            # Sincronização
            barrier.wait()
            self.timestamp_logger.log_timestamp('Post-Barrier', id(driver))

            # Clique
            self.logger.info("🖱️ Executando clique...")
            elemento.click()
            self.timestamp_logger.log_timestamp('Post-Click', id(driver))
            self.logger.info("🎯 Clique executado com sucesso!")
            return True

        except Exception as e:
            self.logger.error(f"❌ Erro ao executar clique [XPath: {xpath}]: {e}")
            return False

    def execute_synchronized_clicks(self, drivers, xpaths):
        """Executa cliques sincronizados com múltiplos navegadores."""
        if len(drivers) != len(xpaths):
            self.logger.error("⚠️ Número de drivers e XPaths incompatível.")
            return False

        self.logger.info(f"🚀 Iniciando cliques sincronizados para {len(drivers)} navegadores...")
        barrier = threading.Barrier(len(drivers))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            self.logger.info("🌟 Pool de threads inicializado")
            futures = [
                executor.submit(self.execute_synchronized_click, driver, xpath, barrier)
                for driver, xpath in zip(drivers, xpaths)
            ]
            resultados = [future.result() for future in as_completed(futures)]

        success = all(resultados)
        if success:
            self.logger.info("🎉 Cliques sincronizados executados com sucesso!")
        else:
            self.logger.error("💥 Falha na execução dos cliques sincronizados")

        return success
