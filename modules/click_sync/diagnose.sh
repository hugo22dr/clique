#!/bin/bash

echo "=== Diagnóstico de Sistema ==="
echo "Memória:"
free -h
echo
echo "Cache do Sistema:"
cat /proc/sys/vm/drop_caches
echo
echo "Módulos carregados:"
lsmod | grep click
echo
echo "Logs do kernel:"
dmesg | tail -n 20
echo
echo "Estado da memória do kernel:"
cat /proc/meminfo
echo
echo "=== Fim do Diagnóstico ==="