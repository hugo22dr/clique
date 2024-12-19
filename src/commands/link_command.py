from log_config import get_logger

logger = get_logger(__name__)

def executar_comando_new_link(drivers, navegadores_config):
    """Executa comando para configurar novo link."""
    for index, driver in enumerate(drivers):
        if driver is None or not driver.session_id:
            logger.warning(f"[Navegador {index + 1}] Sessão inválida. Pule este navegador.")
            continue
        novo_link = input(f"Digite o novo link para o navegador {index + 1}: ").strip()
        if novo_link:
            try:
                logger.info(f"[Navegador {index + 1}] Carregando link: {novo_link}")
                driver.get(novo_link)
                navegadores_config[index]["link"] = novo_link
                navegadores_config[index]["xpaths"] = []
                logger.info(f"[Navegador {index + 1}] Link configurado com sucesso.")
            except Exception as e:
                logger.error(f"[Navegador {index + 1}] Erro ao carregar o link: {e}")
        else:
            logger.warning(f"[Navegador {index + 1}] Nenhum link fornecido. Pulando.")