#!/bin/bash

echo "=== Verificando Módulo Click Sync ==="

# Verifica se o módulo está carregado
if lsmod | grep -q "click_sync"; then
    echo "[OK] Módulo está carregado"
else
    echo "[ERRO] Módulo não está carregado"
    exit 1
fi

# Verifica o dispositivo
if [ -c "/dev/precise_sync" ]; then
    echo "[OK] Dispositivo /dev/precise_sync existe"
    ls -l /dev/precise_sync
else
    echo "[ERRO] Dispositivo não encontrado"
    exit 1
fi

# Verifica permissões RT
if grep -q "kernel.sched_rt_runtime_us=-1" /etc/sysctl.conf; then
    echo "[OK] Configuração RT está correta"
else
    echo "[AVISO] Configuração RT pode precisar de ajuste"
    echo "Adicione: kernel.sched_rt_runtime_us=-1 em /etc/sysctl.conf"
fi

# Verifica configuração de CPU
echo "=== Configuração de CPU ==="
lscpu | grep -E "Core|Socket|Thread|NUMA|CPU\(s\)"

# Verifica status do dispositivo
echo "=== Status do Dispositivo ==="
if [ -f "/sys/class/precise_sync_class/precise_sync/status" ]; then
    cat /sys/class/precise_sync_class/precise_sync/status
else
    echo "[INFO] Status não disponível"
fi

# Verifica logs do kernel relacionados
echo "=== Logs do Kernel ==="
dmesg | grep -i "click sync" | tail -n 5

echo "=== Verificação Completa ==="