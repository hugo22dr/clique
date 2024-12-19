from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from log_config import get_logger

logger = get_logger(__name__)

def verificar_e_restaurar_sessao(driver, index):
    """Verifica se o navegador está ativo e tenta restaurar a sessão se necessário."""
    logger.info(f"[Sessão] Verificando sessão para o navegador {index + 1}...")
    try:
        if driver.session_id is None:
            logger.warning(f"[Sessão] Sessão perdida no navegador {index + 1}. Tentando recuperar...")
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            logger.info(f"[Sessão] Recuperação bem-sucedida no navegador {index + 1}.")
            desativar_animacoes_e_transicoes(driver, index)
            return True
        driver.title
        logger.info(f"[Sessão] Sessão ativa no navegador {index + 1}.")
        desativar_animacoes_e_transicoes(driver, index)
        return True
    except Exception as e:
        logger.error(f"[Sessão] Falha ao verificar ou restaurar sessão no navegador {index + 1}: {e}")
        return False

def localizar_elementos_em_abas(driver, index, xpaths):
    """Localiza elementos nos navegadores usando XPaths configurados."""
    if driver is None or not verificar_e_restaurar_sessao(driver, index):
        logger.warning(f"[Navegador {index + 1}] Sessão não operacional. Ignorando este navegador.")
        return []

    encontrados = []
    logger.info(f"[Navegador {index + 1}] Iniciando localização de elementos com {len(xpaths)} XPaths...")

    for xpath in xpaths:
        try:
            elemento = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            if elemento and elemento.tag_name.lower() in {"button", "input", "div"}:
                encontrados.append((xpath, elemento))
                logger.info(f"[Navegador {index + 1}] Elemento interativo encontrado: {xpath}")
            else:
                logger.info(f"[Navegador {index + 1}] Elemento encontrado, mas não é considerado interativo: {xpath}")

        except Exception as e:
            logger.warning(f"[Navegador {index + 1}] Falha ao localizar elemento para XPath '{xpath}': {e}")

    logger.info(f"[Navegador {index + 1}] Total de elementos interativos localizados: {len(encontrados)}")
    return encontrados

def clicar_elementos_em_navegador(driver, elementos, index):
    """Clica no primeiro botão encontrado no navegador."""
    if not elementos:
        logger.warning(f"[Navegador {index + 1}] Nenhum elemento disponível para clicar.")
        return

    logger.info(f"[Navegador {index + 1}] Tentando clicar em {len(elementos)} elemento(s)...")
    clicou_botao = False

    for xpath, elemento in elementos:
        if clicou_botao:
            break
        try:
            elemento = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", elemento)
            logger.info(f"[Navegador {index + 1}] Botão clicado com sucesso: {xpath}")
            clicou_botao = True
        except Exception as e:
            logger.warning(f"[Navegador {index + 1}] Erro ao clicar no elemento '{xpath}': {e}")

    if not clicou_botao:
        logger.warning(f"[Navegador {index + 1}] Não foi possível clicar em nenhum botão.")

def desativar_animacoes_e_transicoes(driver, index):
    """Desativa animações e transições CSS no navegador."""
    try:
        driver.execute_script("""
            var style = document.createElement('style');
            style.type = 'text/css';
            style.innerHTML = '* { animation: none !important; transition: none !important; }';
            document.head.appendChild(style);
        """)
        logger.info(f"[Navegador {index + 1}] Animações e transições desativadas.")
    except Exception as e:
        logger.warning(f"[Navegador {index + 1}] Falha ao desativar animações e transições: {e}")