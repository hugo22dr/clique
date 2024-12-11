obj-m += click_sync_kernel.o

KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	@echo "Compilando módulo click_sync_kernel..."
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

load:
	@echo "Verificando se módulo já está carregado..."
	@if lsmod | grep -q "click_sync_kernel"; then \
		echo "Removendo módulo antigo..."; \
		sudo rmmod click_sync_kernel || exit 1; \
	fi
	@echo "Carregando módulo..."
	sudo insmod click_sync_kernel.ko
	@echo "Módulo carregado. Verificando logs..."
	@dmesg | tail -n 5

unload:
	@echo "Removendo módulo..."
	@if lsmod | grep -q "click_sync_kernel"; then \
		sudo rmmod click_sync_kernel; \
		echo "Módulo removido com sucesso."; \
	else \
		echo "Módulo não estava carregado."; \
	fi