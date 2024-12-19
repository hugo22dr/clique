# Contém a lógica para processar os comandos no loop principal.

from src.commands import executar_comando
from log_config import get_logger

logger = get_logger(__name__)

def processar_comandos(drivers, navegadores_config):
    """Processa o loop principal de comandos."""
    while True:
        try:
            comando = input("Digite um comando ('add', 'localize', 'click', 'new link', ou 'exit'): ").strip().lower()
            if comando in {"new link", "add", "localize", "click"}:
                executar_comando(comando, drivers, navegadores_config)
            elif comando == "exit":
                logger.info("[Sistema] Encerrando programa.")
                break
            else:
                logger.warning("[Sistema] Comando inválido.")
        except KeyboardInterrupt:
            logger.info("[Sistema] Interrupção manual detectada. Encerrando programa...")
            break
        except Exception as e:
            logger.error(f"[Sistema] Erro ao executar comando: {e}")
