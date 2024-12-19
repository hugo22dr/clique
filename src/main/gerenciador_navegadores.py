from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from src.navegador.inicializador import abrir_navegador
from config import drivers
from log_config import get_logger

logger = get_logger(__name__)

def abrir_todos_navegadores(num_instancias):
    """Abre navegadores em paralelo e aguarda que todos estejam prontos."""
    barrier = Barrier(num_instancias)
    opened_drivers = []

    def abrir_com_barreira(index):
        try:
            logger.info(f"Iniciando abertura do navegador {index + 1}...")
            driver = abrir_navegador(index)
            logger.info(f"Navegador {index + 1} aberto com sucesso.")
            return driver
        except Exception as e:
            logger.error(f"Erro ao abrir navegador {index + 1}: {e}")
            return None
        finally:
            barrier.wait()

    with ThreadPoolExecutor(max_workers=num_instancias) as executor:
        futures = [executor.submit(abrir_com_barreira, i) for i in range(num_instancias)]
        for future in futures:
            driver = future.result()
            if driver:
                opened_drivers.append(driver)

    return opened_drivers

def fechar_navegadores():
    """Fecha todos os navegadores abertos."""
    try:
        for driver in drivers:
            if driver and hasattr(driver, 'session_id') and driver.session_id:
                driver.quit()
        logger.info("[Sistema] Todos os navegadores foram encerrados.")
    except Exception as e:
        logger.error(f"[Sistema] Erro ao fechar navegadores: {e}")
