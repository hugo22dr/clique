from log_config import get_logger  # Importa o logger do módulo log_config
from navegador_op import verificar_e_restaurar_sessao

# Inicializa o logger para este módulo
logger = get_logger(__name__)

# config.py

# config.py

# Configurações globais
NUM_INSTANCIAS = 2  # Defina o número de instâncias de navegadores
drivers = []  # Lista global para armazenar os navegadores
navegadores_config = {i: {"link": None, "xpaths": []} for i in range(NUM_INSTANCIAS)}

def validar_configuracao():
    """
    Valida a configuração de cada navegador, verificando drivers, links e XPaths.
    Retorna uma lista com os índices dos navegadores válidos.
    """
    validos = []
    logger.info("[Validação] Iniciando validação de configurações...")

    for index, driver in enumerate(drivers):
        logger.info(f"[Validação] Verificando Navegador {index + 1}...")

        # Verifica o driver
        if driver is None:
            logger.error(f"[Validação] Navegador {index + 1}: Driver inexistente.")
            continue
        if not driver.session_id:
            logger.error(f"[Validação] Navegador {index + 1}: Sessão inativa.")
            continue
        logger.info(f"[Validação] Navegador {index + 1}: Sessão ativa e válida.")

        # Verifica o link configurado
        config = navegadores_config[index]
        link_configurado = config.get("link")
        if not link_configurado:
            logger.warning(f"[Validação] Navegador {index + 1}: Nenhum link configurado.")
            continue

        # Testa se o link está realmente carregado no navegador
        try:
            current_url = driver.current_url
            if not current_url.startswith(link_configurado):
                logger.warning(f"[Validação] Navegador {index + 1}: URL atual não corresponde ao link configurado.")
                logger.debug(f"[Validação] Navegador {index + 1}: URL atual = {current_url}, esperado = {link_configurado}")
                continue
        except Exception as e:
            logger.error(f"[Validação] Navegador {index + 1}: Erro ao verificar a URL: {e}")
            continue

        # Verifica os XPaths configurados
        xpaths_configurados = config.get("xpaths", [])
        if not xpaths_configurados:
            logger.warning(f"[Validação] Navegador {index + 1}: Nenhum XPath configurado.")
            continue

        # Navegador válido
        logger.info(f"[Validação] Navegador {index + 1}: Configuração válida.")
        validos.append(index)

    # Resumo final da validação
    if not validos:
        logger.warning("[Validação] Nenhum navegador válido encontrado.")
    else:
        logger.info(f"[Validação] Navegadores válidos: {validos}")

    return validos
