from log_config import get_logger
from src.navegador.operacoes import localizar_elementos_em_abas

logger = get_logger(__name__)

def executar_comando_localize(drivers, navegadores_config):
    """Executa comando para localizar elementos."""
    for index, driver in enumerate(drivers):
        config = navegadores_config[index]
        if not config["link"] or not config["xpaths"]:
            logger.warning(f"[Navegador {index + 1}] Não configurado corretamente. Pulando.")
            continue
        try:
            encontrados = localizar_elementos_em_abas(driver, index, config["xpaths"])
            if encontrados:
                logger.info(f"[Navegador {index + 1}] Elementos encontrados: {len(encontrados)}")
            else:
                logger.warning(f"[Navegador {index + 1}] Nenhum elemento localizado.")
        except Exception as e:
            logger.error(f"[Navegador {index + 1}] Erro ao localizar elementos: {e}")