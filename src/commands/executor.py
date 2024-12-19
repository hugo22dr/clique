"""Módulo principal para execução de comandos."""
from log_config import get_logger
from src.commands.types import CommandType
from src.commands.add_command import executar_comando_add
from src.commands.click_command import executar_cliques_simultaneos
from src.commands.link_command import executar_comando_new_link
from src.commands.locate_command import executar_comando_localize

logger = get_logger(__name__)

def executar_comando(comando, drivers, navegadores_config):
    """
    Executa o comando especificado nos navegadores.
    
    Args:
        comando: Tipo do comando a ser executado
        drivers: Lista de drivers dos navegadores
        navegadores_config: Configuração dos navegadores
    """
    try:
        command_type = CommandType(comando)
    except ValueError:
        logger.warning("[Sistema] Comando inválido.")
        return
        
    command_handlers = {
        CommandType.NEW_LINK: executar_comando_new_link,
        CommandType.ADD: executar_comando_add,
        CommandType.CLICK: executar_cliques_simultaneos,
        CommandType.LOCATE: executar_comando_localize
    }
    
    handler = command_handlers.get(command_type)
    if handler:
        handler(drivers, navegadores_config)