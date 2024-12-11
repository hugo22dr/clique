from log_config import get_logger
from navegador_op import verificar_e_restaurar_sessao
import os
import psutil

logger = get_logger(__name__)

# Cálculo automático de instâncias baseado nos recursos
def calcular_num_instancias():
    """Calcula o número ótimo de instâncias baseado nos recursos do sistema."""
    try:
        # Obtém informações do sistema
        cpu_count = os.cpu_count()
        mem_info = psutil.virtual_memory()
        mem_available_gb = mem_info.available / (1024 ** 3)  # Converte para GB
        
        # Reserva 2 cores para sistema
        cores_disponíveis = max(cpu_count - 2, 2)
        
        # Calcula baseado em memória (2GB por instância)
        max_por_memoria = int(mem_available_gb / 2)
        
        # Usa o menor valor entre cores disponíveis e limite de memória
        num_instancias = min(cores_disponíveis, max_por_memoria)
        
        # Garante pelo menos 2 instâncias
        return max(num_instancias, 2)
    except:
        return 2  # Valor padrão seguro

# Configurações globais otimizadas
NUM_INSTANCIAS = 2
drivers = []
navegadores_config = {i: {"link": None, "xpaths": []} for i in range(NUM_INSTANCIAS)}

# Configurações de performance
PERFORMANCE_CONFIG = {
    'cores_por_instancia': max(2, (os.cpu_count() - 2) // NUM_INSTANCIAS),
    'memoria_por_instancia': '2G',
    'prioridade_base': -10,
    'distribuicao_ccx': True,  # Habilita distribuição por CCX
}

def validar_configuracao():
    """Valida a configuração de cada navegador com verificações adicionais."""
    validos = []
    logger.info("[Validação] Iniciando validação de configurações...")
    
    # Verifica recursos do sistema primeiro
    mem_info = psutil.virtual_memory()
    if mem_info.percent > 90:
        logger.warning("[Validação] Sistema com pouca memória disponível")
    
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 80:
        logger.warning("[Validação] Alta utilização de CPU detectada")
    
    for index, driver in enumerate(drivers):
        logger.info(f"[Validação] Verificando Navegador {index + 1}...")
        
        # Verificação de driver e sessão
        if not _validar_driver(driver, index):
            continue
            
        # Verificação de configuração
        config = navegadores_config[index]
        if not _validar_config(config, driver, index):
            continue
            
        # Verificação de performance
        if not _validar_performance(driver, index):
            continue
        
        # Navegador válido
        logger.info(f"[Validação] Navegador {index + 1}: Configuração válida.")
        validos.append(index)
    
    _exibir_resumo_validacao(validos)
    return validos

def _validar_driver(driver, index):
    """Valida o driver e sua sessão."""
    if driver is None:
        logger.error(f"[Validação] Navegador {index + 1}: Driver inexistente.")
        return False
    
    if not driver.session_id:
        logger.error(f"[Validação] Navegador {index + 1}: Sessão inativa.")
        return False
    
    if not verificar_e_restaurar_sessao(driver, index):
        logger.error(f"[Validação] Navegador {index + 1}: Falha ao verificar sessão.")
        return False
        
    logger.info(f"[Validação] Navegador {index + 1}: Sessão ativa e válida.")
    return True

def _validar_config(config, driver, index):
    """Valida configurações específicas do navegador."""
    link_configurado = config.get("link")
    if not link_configurado:
        logger.warning(f"[Validação] Navegador {index + 1}: Nenhum link configurado.")
        return False
    
    try:
        current_url = driver.current_url
        if not current_url.startswith(link_configurado):
            logger.warning(f"[Validação] Navegador {index + 1}: URL não corresponde.")
            logger.debug(f"[Validação] URL atual = {current_url}, esperado = {link_configurado}")
            return False
    except Exception as e:
        logger.error(f"[Validação] Erro ao verificar URL: {e}")
        return False
    
    xpaths_configurados = config.get("xpaths", [])
    if not xpaths_configurados:
        logger.warning(f"[Validação] Navegador {index + 1}: Nenhum XPath configurado.")
        return False
        
    return True

def _validar_performance(driver, index):
    """Valida métricas de performance do navegador."""
    try:
        # Verifica uso de memória do processo
        process = psutil.Process(driver.service.process.pid)
        mem_percent = process.memory_percent()
        
        if mem_percent > 20:  # Se usar mais de 20% da RAM
            logger.warning(f"[Validação] Navegador {index + 1}: Alto uso de memória ({mem_percent:.1f}%)")
            return False
            
        return True
    except:
        return True  # Ignora erros na verificação de performance

def _exibir_resumo_validacao(validos):
    """Exibe um resumo final da validação."""
    if not validos:
        logger.warning("[Validação] Nenhum navegador válido encontrado.")
    else:
        logger.info(f"[Validação] Navegadores válidos: {validos}")
