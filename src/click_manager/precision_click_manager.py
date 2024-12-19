import os
import logging
import threading
from sync_constants import SyncDevice
from .timestamp_logger import PreciseTimestampLogger
from .sync_executor import SynchronizedClickExecutor
from .atomic_click import AtomicClickExecutor

class LinuxPrecisionClickManager:
    def __init__(self, max_workers=None, logger=None):
        self.max_workers = max_workers or max(2, os.cpu_count() - 2)
        self.logger = logger or logging.getLogger(__name__)
        self.sync_device = SyncDevice()
        self.ccx_size = 6
        
        # Inicializa loggers e executores
        self.timestamp_logger = PreciseTimestampLogger(self.logger)
        
        # Inicializa executores
        self.sync_executor = SynchronizedClickExecutor(
            self.logger, 
            self.timestamp_logger, 
            self.max_workers
        )
        
        # Tenta inicializar o executor atômico
        try:
            self.atomic_executor = AtomicClickExecutor(self.logger)
            self.has_atomic = True
            self.logger.info("Executor atômico inicializado com sucesso")
        except Exception as e:
            self.has_atomic = False
            self.atomic_executor = None
            self.logger.warning(f"Executor atômico não disponível: {e}")
    
    def execute_synchronized_clicks(self, drivers, xpaths, force_legacy=False):
        """
        Executa cliques sincronizados com suporte a modo atômico.
        
        Args:
            drivers: Lista de WebDrivers
            xpaths: Lista de XPaths
            force_legacy: Força uso do executor legacy mesmo se atomic estiver disponível
            
        Returns:
            bool: True se sucesso, False caso contrário
        """
        # Log início da execução
        self.logger.info(f"Iniciando execução sincronizada para {len(drivers)} navegadores")
        
        try:
            # Decide qual executor usar
            use_atomic = self.has_atomic and not force_legacy
            
            if use_atomic:
                self.logger.info("Usando executor atômico")
                # Registra timestamp pré-execução
                for driver in drivers:
                    self.timestamp_logger.log_timestamp('Pre-Atomic', id(driver))
                    
                # Executa cliques atômicos
                result = self.atomic_executor.execute_synchronized_clicks(drivers, xpaths)
                
                # Registra timestamp pós-execução
                for driver in drivers:
                    self.timestamp_logger.log_timestamp('Post-Atomic', id(driver))
            else:
                self.logger.info("Usando executor legacy")
                # Usa implementação existente
                result = self.sync_executor.execute_synchronized_clicks(drivers, xpaths)
            
            # Analisa timestamps
            self.timestamp_logger.analyze_timestamps()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro durante execução sincronizada: {e}")
            return False
    
    def cleanup(self):
        """Limpa recursos de todos os componentes."""
        try:
            # Limpa executor legacy
            if hasattr(self.sync_executor, 'cleanup'):
                self.sync_executor.cleanup()
            
            # Limpa executor atômico
            if self.atomic_executor:
                self.atomic_executor.cleanup()
                
            self.logger.info("Recursos limpos com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro durante limpeza: {e}")