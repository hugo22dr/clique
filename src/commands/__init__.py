"""Módulo de gerenciamento de comandos."""
from .executor import executar_comando
from .types import CommandType

__all__ = ['executar_comando', 'CommandType']