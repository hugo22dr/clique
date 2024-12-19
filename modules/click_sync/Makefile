# Nome e objetos do módulo
obj-m += click_sync.o
click_sync-objs := click_sync_main.o click_sync_barrier.o click_sync_utils.o

# Diretórios
KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Opções de compilação extras
ccflags-y := -O3 -march=native
ccflags-y += -Wall -Wextra

# Alvos principais
all:
	@echo "Compilando módulo click_sync..."
	$(MAKE) -C $(KDIR) M=$(PWD) modules
	@echo "Compilação concluída."

clean:
	@echo "Limpando arquivos de compilação..."
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	@echo "Limpeza concluída."

install:
	@echo "Instalando módulo..."
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install
	depmod -a
	@echo "Instalação concluída."

check_memory:
	@echo "=== Verificando estado da memória ==="
	@free -h
	@echo "\n=== Cache do sistema ==="
	@cat /proc/sys/vm/drop_caches
	@echo "\n=== Limpando cache do sistema ==="
	@sudo sync
	@sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
	@echo "Cache limpo."

load:
	@echo "Verificando se módulo já está carregado..."
	@if lsmod | grep -q "click_sync"; then \
		echo "Removendo módulo antigo..."; \
		sudo rmmod click_sync || exit 1; \
		sleep 1; \
	fi
	@echo "Preparando sistema..."
	@sudo sync
	@sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
	@echo "Carregando módulo..."
	@sudo insmod click_sync.ko
	@echo "Módulo carregado. Verificando logs..."
	@dmesg | tail -n 5
	@echo "Verificando dispositivo..."
	@ls -l /dev/precise_sync || echo "AVISO: Dispositivo não criado!"
	@echo "Configurando permissões..."
	@sudo chmod 666 /dev/precise_sync 2>/dev/null || echo "AVISO: Não foi possível configurar permissões"

unload:
	@echo "Removendo módulo..."
	@if lsmod | grep -q "click_sync"; then \
		sudo rmmod click_sync; \
		echo "Módulo removido com sucesso."; \
	else \
		echo "Módulo não estava carregado."; \
	fi

reload: unload clean all check_memory load

diagnose:
	@echo "=== Diagnóstico do Sistema ==="
	@echo "\nMemória do Sistema:"
	@free -h
	@echo "\nCache do Sistema:"
	@cat /proc/sys/vm/drop_caches
	@echo "\nMódulos Carregados:"
	@lsmod | grep click
	@echo "\nLogs do Kernel:"
	@dmesg | tail -n 20
	@echo "\nEstado da Memória do Kernel:"
	@cat /proc/meminfo
	@echo "\nStatus do Dispositivo:"
	@ls -l /dev/precise_sync 2>/dev/null || echo "Dispositivo não encontrado"
	@echo "\nConfigurações de CPU:"
	@lscpu | grep -E "Core|Socket|Thread|NUMA|CPU\(s\)"
	@echo "\n=== Fim do Diagnóstico ==="

# Declaração de alvos falsos
.PHONY: all clean install load unload reload check_memory diagnose