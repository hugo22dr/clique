from selenium.webdriver.chrome.options import Options
from undetected_chromedriver import Chrome
from selenium_stealth import stealth
from fake_useragent import UserAgent
from log_config import get_logger
import random

logger = get_logger(__name__)

def criar_perfil_navegador():
    """
    Cria um perfil de navegador único para cada instância
    """
    perfis = [
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Win32",
            "resolution": (1920, 1080)
        },
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "platform": "Win32",
            "resolution": (1366, 768)
        },
        {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "platform": "Linux x86_64",
            "resolution": (1440, 900)
        }
    ]
    return random.choice(perfis)

def abrir_navegador(index=0):
    """
    Abre uma instância de navegador otimizada para cliques simultâneos
    """
    options = Options()
    
    # Configurações críticas para performance
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    
    # Configurações para evitar detecção sem impactar performance
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-3d-apis")
    
    try:
        # Seleciona perfil aleatório mas mantém consistente durante a sessão
        perfil = criar_perfil_navegador()
        options.add_argument(f"user-agent={perfil['user_agent']}")
        
        driver_path = "/home/hugo22dr/.local/share/undetected_chromedriver/undetected_chromedriver/chromedriver"
        driver = Chrome(options=options, driver_executable_path=driver_path)

        
        # Configuração stealth leve
        stealth(
            driver,
            languages=["pt-BR", "pt", "en-US"],
            vendor="Google Inc.",
            platform=perfil['platform'],
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        
        # Define resolução consistente
        largura, altura = perfil['resolution']
        driver.set_window_size(largura, altura)
        
        # Configurações mínimas de rede para evitar detecção
        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
            'headers': {
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Connection': 'keep-alive'
            }
        })
        
        # Timeout adequado para operações rápidas
        driver.set_page_load_timeout(15)
        
        return driver
    except Exception as e:
        logger.error(f"Erro ao abrir navegador {index}: {e}")
        raise

def verificar_e_restaurar_sessao(driver, index):
    """
    Verifica se o navegador está ativo de forma rápida
    """
    try:
        if driver is None or driver.session_id is None:
            return False
        # Teste rápido de sessão
        driver.current_url
        return True
    except Exception as e:
        logger.error(f"[Sessão] Erro no navegador {index + 1}: {e}")
        return False

def reiniciar_navegador(driver, index):
    """
    Reinicia o navegador mantendo o mesmo perfil
    """
    try:
        if driver:
            driver.quit()
    except Exception:
        pass
    
    try:
        novo_driver = abrir_navegador(index)
        logger.info(f"[Navegador {index + 1}] Reiniciado com sucesso.")
        return novo_driver
    except Exception as e:
        logger.error(f"[Navegador {index + 1}] Falha ao reiniciar: {e}")
        return None

def fechar_todos_navegadores(drivers):
    """
    Fecha todas as instâncias de navegadores de forma limpa
    """
    for driver in drivers:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass