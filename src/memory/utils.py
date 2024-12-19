"""Utilitários para o gerenciador de memória."""
import os
import subprocess
from typing import List, Tuple

def run_with_sudo(command: List[str]) -> Tuple[bool, str]:
    """
    Executa comando com sudo se necessário.
    
    Args:
        command: Lista com o comando a ser executado
        
    Returns:
        Tuple[bool, str]: Status de sucesso e mensagem
    """
    try:
        cmd_prefix = [] if os.geteuid() == 0 else ['sudo']
        result = subprocess.run(
            cmd_prefix + command,
            check=True,
            capture_output=True,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, str(e)

def set_sysfs_value(path: str, value: str) -> Tuple[bool, str]:
    """
    Define valor em arquivo sysfs.
    
    Args:
        path: Caminho do arquivo
        value: Valor a ser definido
        
    Returns:
        Tuple[bool, str]: Status de sucesso e mensagem
    """
    if not os.path.exists(path):
        return False, f"Path não existe: {path}"
        
    success, message = run_with_sudo(['sh', '-c', f'echo {value} > {path}'])
    return success, message