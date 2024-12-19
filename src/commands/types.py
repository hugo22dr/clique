"""Tipos e constantes para comandos."""
from enum import Enum

class CommandType(Enum):
    NEW_LINK = "new link"
    ADD = "add"
    CLICK = "click"
    LOCATE = "localize"