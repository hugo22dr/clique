import logging
from colorama import Fore, Style

# Classe de formatação personalizada para logs com cores
class LogFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: f"{Fore.BLUE}%(asctime)s - [DEBUG] - %(message)s{Style.RESET_ALL}",
        logging.INFO: f"{Fore.GREEN}%(asctime)s - [INFO] - %(message)s{Style.RESET_ALL}",
        logging.WARNING: f"{Fore.YELLOW}%(asctime)s - [WARNING] - %(message)s{Style.RESET_ALL}",
        logging.ERROR: f"{Fore.RED}%(asctime)s - [ERROR] - %(message)s{Style.RESET_ALL}",
        logging.CRITICAL: f"{Fore.RED}{Style.BRIGHT}%(asctime)s - [CRITICAL] - %(message)s{Style.RESET_ALL}",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(message)s")
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

# Configuração global de logging
def setup_logging(level=logging.WARNING, log_file=None):
    # Evita reconfigurar múltiplos handlers
    if logging.getLogger().hasHandlers():
        return

    # Handler de log para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LogFormatter())

    # Configura o logger principal
    logging.basicConfig(
        level=level,
        handlers=[console_handler],
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Adiciona handler para arquivo, se especificado
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        logging.getLogger().addHandler(file_handler)

# Função utilitária para obter loggers específicos
def get_logger(name, level=logging.INFO, log_file=None):
    setup_logging(level=level, log_file=log_file)
    return logging.getLogger(name)
