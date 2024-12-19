import os
from log_config import get_logger

logger = get_logger(__name__)

def verificar_privilegios():
    """Verifica se o programa está sendo executado com privilégios necessários."""
    if os.geteuid() != 0:
        logger.warning("[Sistema] Programa não está rodando como root. Algumas otimizações podem não funcionar.")
        logger.info("[Sistema] Para funcionalidade completa, execute com: sudo python main.py")
        return False
    return True
