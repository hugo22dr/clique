import signal
import os
import logging
from threading import Event
from typing import Callable, Optional

class SignalHandler:
    def __init__(self, 
                 logger: logging.Logger, 
                 shutdown_callback: Optional[Callable] = None):
        self.logger = logger
        self.shutdown_event = Event()
        self.shutdown_callback = shutdown_callback
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Configura handlers para todos os sinais relevantes."""
        signals = [
            signal.SIGTERM, signal.SIGINT, signal.SIGQUIT,
            signal.SIGSEGV, signal.SIGABRT
        ]
        for sig in signals:
            try:
                signal.signal(sig, self._handle_signal)
            except Exception as e:
                self.logger.warning(f"Não foi possível configurar handler para sinal {sig}: {e}")
        
        self.logger.info("Manipuladores de sinais registrados com sucesso.")

    def _handle_signal(self, signum, frame):
        """Handler central para todos os sinais."""
        if self.shutdown_event.is_set():
            return
        
        self.logger.info(f"Sinal {signum} recebido. Iniciando desligamento seguro...")
        self.shutdown_event.set()
        
        if self.shutdown_callback:
            self.shutdown_callback()

    def wait_for_shutdown(self, timeout: Optional[float] = None):
        """Aguarda evento de shutdown."""
        self.shutdown_event.wait(timeout)
        return self.shutdown_event.is_set()
