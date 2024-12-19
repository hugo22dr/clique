from .inicializador import abrir_navegador
from .operacoes import verificar_e_restaurar_sessao
from log_config import get_logger
import time

logger = get_logger(__name__)

def reiniciar_navegador(driver, index):
    """Reinicia o navegador de forma segura."""
    try:
        if driver:
            try:
                driver.quit()
            except:
                pass
            time.sleep(1)
            
        novo_driver = abrir_navegador(index)
        logger.info(f"[Navegador {index + 1}] Reiniciado com sucesso.")
        return novo_driver
    except Exception as e:
        logger.error(f"[Navegador {index + 1}] Falha ao reiniciar: {e}")
        return None

def fechar_todos_navegadores(drivers):
    """Fecha todos os navegadores de forma segura."""
    for driver in drivers:
        try:
            if driver:
                driver.execute_script("window.onbeforeunload = null;")
                try:
                    driver.quit()
                except:
                    pass
        except:
            pass