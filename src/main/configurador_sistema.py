# src/main/configurador_sistema.py

from src.memory import MemoryManager
from src.sistema.gerenciador_sistema_avancado import EnhancedSystemManager
from src.click_manager.precision_click_manager import LinuxPrecisionClickManager
from log_config import get_logger

logger = get_logger(__name__)

def inicializar_sistema():
    """Inicializa memória, CPU e gerenciadores do sistema."""
    memoria_manager = MemoryManager(logger)
    sistema_manager = EnhancedSystemManager(logger)
    
    # Configuração
    memoria_manager.lock_memory()  # Mudou de configurar_memoria_locked para lock_memory
    sistema_manager.optimize_cpu_affinity()
    sistema_manager.set_process_priority(-10)
    sistema_manager.optimize_memory_settings()
    
    click_manager = LinuxPrecisionClickManager()
    
    return memoria_manager, sistema_manager, click_manager