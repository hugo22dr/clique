#!/bin/bash

echo "Iniciando configuração do dispositivo..."

# Define o diretório do módulo
MODULE_DIR="modules"

# Função para checar se comando foi bem sucedido
check_error() {
    if [ $? -ne 0 ]; then
        echo "Erro: $1"
        exit 1
    fi
}

# Remove módulo antigo
if lsmod | grep -q "click_sync_kernel"; then
    echo "Removendo módulo antigo..."
    sudo rmmod click_sync_kernel
    check_error "Falha ao remover módulo antigo"
fi

# Carrega novo módulo
echo "Carregando novo módulo..."
cd $MODULE_DIR
sudo insmod click_sync_kernel.ko
check_error "Falha ao carregar módulo"
cd ..

# Espera um momento e verifica se módulo foi carregado
sleep 2
if ! lsmod | grep -q "click_sync_kernel"; then
    echo "Erro: Módulo não foi carregado corretamente"
    exit 1
fi

# Encontra major number
echo "Procurando major number..."
major=$(dmesg | grep "Click Sync" | tail -n 1 | grep -o "major=[0-9]*" | cut -d= -f2)
if [ -z "$major" ]; then
    echo "Erro: Não foi possível encontrar major number"
    exit 1
fi

# Remove dispositivo antigo
echo "Removendo dispositivo antigo se existir..."
sudo rm -f /dev/click_sync

# Cria novo dispositivo
echo "Criando novo dispositivo..."
sudo mknod /dev/click_sync c $major 0
check_error "Falha ao criar dispositivo"

# Define permissões
echo "Configurando permissões..."
sudo chmod 666 /dev/click_sync
check_error "Falha ao definir permissões"

sudo chown root:root /dev/click_sync
check_error "Falha ao definir proprietário"

# Verifica se dispositivo existe e tem permissões corretas
if [ ! -c "/dev/click_sync" ]; then
    echo "Erro: Dispositivo não foi criado corretamente"
    exit 1
fi

echo "Verificando permissões finais:"
ls -l /dev/click_sync

echo "Configuração completa!"