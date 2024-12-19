from selenium.webdriver.chrome.options import Options
from undetected_chromedriver import Chrome
from .perfil import criar_perfil_navegador
from log_config import get_logger
import time

logger = get_logger(__name__)

def abrir_navegador(index=0, max_retries=3):
    """Abre navegador com proteções anti-detecção e garantia de conexão."""
    for attempt in range(max_retries):
        try:
            options = Options()
            
            # Configurações críticas
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Configurações de performance
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-notifications")
            
            # Importante: Mantém conexão estável
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            
            # Perfil e user agent
            perfil = criar_perfil_navegador()
            options.add_argument(f"user-agent={perfil['user_agent']}")
            
            # Inicialização do driver
            driver = Chrome(
                options=options,
                driver_executable_path="/usr/local/bin/chromedriver"
            )
            
            # Configuração básica
            largura, altura = perfil['resolution']
            driver.set_window_size(largura, altura)
            
            # Verifica conexão
            driver.execute_script("return navigator.userAgent")
            
            # Configurações adicionais após conexão estabelecida
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            # Importante: Aguarda estabilização
            time.sleep(1)
            
            logger.info(f"Navegador {index + 1} aberto com sucesso.")
            return driver
            
        except Exception as e:
            logger.error(f"Tentativa {attempt + 1} falhou ao abrir navegador {index}: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)