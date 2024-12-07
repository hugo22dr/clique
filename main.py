import click_sync
from log_config import get_logger
from navegador import abrir_navegador
from comando_exec import executar_comando
from config import NUM_INSTANCIAS, drivers, navegadores_config
from click_manager import LinuxPrecisionClickManager
from gerenciador_memoria import GerenciadorMemoria
from gerenciador_sistema_avancado import EnhancedSystemManager
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

logger = get_logger(__name__)

def fechar_navegadores():
    """Fecha todos os navegadores abertos."""
    for driver in drivers:
        if driver and driver.session_id:
            driver.quit()
    logger.info("[Sistema] Todos os navegadores foram encerrados.")

def exibir_configuracao():
    """Exibe as configurações atuais (links e XPaths) de todos os navegadores."""
    logger.info("[Sistema] Configuração atual dos navegadores:")
    for index, config in navegadores_config.items():
        link = config.get("link", "Não configurado")
        xpaths = config.get("xpaths", [])
        xpaths = xpaths if xpaths else "Nenhum XPath configurado"
        logger.info(f"  Navegador {index + 1}: Link = {link}, XPaths = {xpaths}")

def abrir_todos_navegadores(num_instancias):
    """Abre navegadores em paralelo e aguarda que todos estejam prontos."""
    barrier = Barrier(num_instancias)
    drivers = []

    def abrir_com_barreira(index):
        driver = None
        try:
            logger.info(f"Iniciando abertura do navegador {index + 1}...")
            driver = abrir_navegador(index)
            logger.info(f"Navegador {index + 1} aberto com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao abrir navegador {index + 1}: {e}")
        finally:
            barrier.wait()  # Aguarda que todos cheguem a este ponto
            return driver

    with ThreadPoolExecutor(max_workers=num_instancias) as executor:
        drivers = list(executor.map(abrir_com_barreira, range(num_instancias)))

    return [driver for driver in drivers if driver is not None]

if __name__ == "__main__":
    click_manager = None
    memoria_manager = GerenciadorMemoria(logger)
    sistema_manager = EnhancedSystemManager(logger)
    
    try:
        # Configurações de sistema e memória
        memoria_manager.configurar_memoria_locked()
        sistema_manager.optimize_cpu_affinity()
        sistema_manager.set_process_priority(high_priority=True)
        
        # Inicialização do gerenciador de cliques
        import click_sync
        click_manager = LinuxPrecisionClickManager(max_workers=NUM_INSTANCIAS)

        
        # Abrir navegadores em paralelo
        drivers.clear()
        drivers.extend(abrir_todos_navegadores(NUM_INSTANCIAS))
        logger.info(f"Todos os {NUM_INSTANCIAS} navegadores foram abertos com sucesso.")

        # Exibir configuração inicial
        exibir_configuracao()

        # Loop principal aguardando comandos
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
                exibir_configuracao()
            except KeyboardInterrupt:
                logger.info("[Sistema] Interrupção manual detectada. Encerrando programa...")
                break
            except Exception as e:
                logger.error(f"[Sistema] Erro ao executar comando: {e}")
    finally:
        # Limpezas gerais
        if click_manager and hasattr(click_manager, "cleanup"):
            click_manager.cleanup()

        fechar_navegadores()
        sistema_manager.graceful_shutdown()
        memoria_manager.limpar_configuracoes()
