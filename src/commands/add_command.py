from log_config import get_logger

logger = get_logger(__name__)

def executar_comando_add(drivers, navegadores_config):
    """Executa comando para adicionar novo XPath."""
    for index, driver in enumerate(drivers):
        config = navegadores_config[index]
        if not config["link"]:
            logger.warning(f"[Navegador {index + 1}] Nenhum link configurado. Pule este navegador.")
            continue
        novo_xpath = input(f"Digite um novo XPath para o navegador {index + 1}: ").strip()
        if novo_xpath:
            if novo_xpath.startswith("//") or novo_xpath.startswith(".//"):
                config["xpaths"].append(novo_xpath)
                logger.info(f"[Navegador {index + 1}] Novo XPath adicionado: {novo_xpath}")
            else:
                logger.warning(f"[Navegador {index + 1}] XPath inválido: {novo_xpath}")
        else:
            logger.info(f"[Navegador {index + 1}] Nenhum XPath foi adicionado.")