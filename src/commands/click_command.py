from log_config import get_logger
from src.click_manager.precision_click_manager import LinuxPrecisionClickManager
from config import validar_configuracao

logger = get_logger(__name__)

def executar_cliques_simultaneos(drivers, navegadores_config):
    """Executa cliques sincronizados em múltiplos navegadores."""
    logger.info("[Clique] Iniciando processo de cliques sincronizados...")
    navegadores_validos = validar_configuracao()
    
    if not navegadores_validos:
        logger.warning("[Clique] Nenhum navegador válido para clique.")
        return

    click_manager = LinuxPrecisionClickManager(max_workers=len(navegadores_validos))
    
    try:
        drivers_validos = []
        xpaths_validos = []
        
        for index in navegadores_validos:
            driver = drivers[index]
            xpath = navegadores_config[index]["xpaths"][0]
            
            drivers_validos.append(driver)
            xpaths_validos.append(xpath)
            
        if not drivers_validos:
            logger.error("[Clique] Nenhum navegador preparado corretamente")
            return
            
        logger.info("[Clique] Navegadores preparados, iniciando sincronização")
        
        resultados = click_manager.execute_synchronized_clicks(
            drivers_validos,
            xpaths_validos
        )
        
        if resultados:
            logger.info("[Clique] Cliques sincronizados executados com sucesso")
        else:
            logger.error("[Clique] Falha na execução dos cliques sincronizados")
    
    except Exception as e:
        logger.error(f"[Clique] Erro durante execução: {e}")
    finally:
        click_manager.cleanup()