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
import sys
import os

logger = get_logger(__name__)

def fechar_navegadores():
    """Fecha todos os navegadores abertos."""
    try:
        for driver in drivers:
            if driver and hasattr(driver, 'session_id') and driver.session_id:
                driver.quit()
        logger.info("[Sistema] Todos os navegadores foram encerrados.")
    except Exception as e:
        logger.error(f"[Sistema] Erro ao fechar navegadores: {e}")

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
    opened_drivers = []

    def abrir_com_barreira(index):
        driver = None
        try:
            logger.info(f"Iniciando abertura do navegador {index + 1}...")
            driver = abrir_navegador(index)
            logger.info(f"Navegador {index + 1} aberto com sucesso.")
            return driver
        except Exception as e:
            logger.error(f"Erro ao abrir navegador {index + 1}: {e}")
            return None
        finally:
            try:
                barrier.wait()
            except Exception as e:
                logger.error(f"Erro na sincronização da barreira para navegador {index + 1}: {e}")

    with ThreadPoolExecutor(max_workers=num_instancias) as executor:
        futures = [executor.submit(abrir_com_barreira, i) for i in range(num_instancias)]
        for future in futures:
            try:
                driver = future.result()
                if driver is not None:
                    opened_drivers.append(driver)
            except Exception as e:
                logger.error(f"Erro ao obter resultado do future: {e}")

    return opened_drivers

def verificar_privilegios():
    """Verifica se o programa está sendo executado com privilégios necessários."""
    if os.geteuid() != 0:
        logger.warning("[Sistema] Programa não está rodando como root. Algumas otimizações podem não funcionar.")
        logger.info("[Sistema] Para funcionalidade completa, execute com: sudo python main.py")
        return False
    return True

if __name__ == "__main__":
    click_manager = None
    memoria_manager = None
    sistema_manager = None
    
    try:
        # Verificação de privilégios
        verificar_privilegios()
        
        # Inicialização dos gerenciadores
        memoria_manager = GerenciadorMemoria(logger)
        sistema_manager = EnhancedSystemManager(logger)
        
        try:
            # Configurações de sistema e memória
            memoria_manager.configurar_memoria_locked()
            sistema_manager.optimize_cpu_affinity()
            sistema_manager.set_process_priority(-10)  # Prioridade alta (-10)
            sistema_manager.optimize_memory_settings()
            
            # Inicialização do gerenciador de cliques
            click_manager = LinuxPrecisionClickManager(max_workers=NUM_INSTANCIAS)
            
            # Abrir navegadores em paralelo
            drivers.clear()
            novos_drivers = abrir_todos_navegadores(NUM_INSTANCIAS)
            
            if not novos_drivers:
                logger.error("[Sistema] Nenhum navegador foi aberto com sucesso.")
                raise RuntimeError("Falha ao abrir navegadores")
                
            drivers.extend(novos_drivers)
            logger.info(f"Todos os {len(drivers)} navegadores foram abertos com sucesso.")
            
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
                    if "fatal" in str(e).lower():
                        logger.error("[Sistema] Erro fatal detectado. Encerrando programa...")
                        break

        except Exception as e:
            logger.error(f"[Sistema] Erro durante a execução: {e}")
            raise

    except Exception as e:
        logger.error(f"[Sistema] Erro crítico: {e}")
        sys.exit(1)
        
    finally:
        logger.info("[Sistema] Iniciando limpeza e encerramento...")
        
        # Limpeza do gerenciador de cliques
        if click_manager and hasattr(click_manager, "cleanup"):
            try:
                click_manager.cleanup()
            except Exception as e:
                logger.error(f"[Sistema] Erro ao limpar click manager: {e}")

        # Fechamento dos navegadores
        fechar_navegadores()
        
        # Limpeza do sistema
        if sistema_manager:
            try:
                sistema_manager.graceful_shutdown()
            except Exception as e:
                logger.error(f"[Sistema] Erro durante graceful shutdown: {e}")
        
        # Limpeza da memória
        if memoria_manager:
            try:
                memoria_manager.limpar_configuracoes()
            except Exception as e:
                logger.error(f"[Sistema] Erro ao limpar configurações de memória: {e}")
        
        logger.info("[Sistema] Programa encerrado.")