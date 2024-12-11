#!/bin/bash

# Caminho para o ambiente virtual
VENV_PATH="./venv"
PYTHON_BIN="$VENV_PATH/bin/python"
PROJECT_ROOT=$(pwd)

# Adiciona o diretório do projeto ao PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Verifica se o ambiente virtual existe
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Erro: Ambiente virtual não encontrado em $VENV_PATH"
    echo "Executando setup inicial..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Ativa o ambiente virtual
source $VENV_PATH/bin/activate

# Compila o módulo click_sync
echo "Compilando módulo click_sync..."
$PYTHON_BIN setup.py build_ext --inplace

# Verifica se o módulo kernel está carregado
if ! lsmod | grep -q "click_sync_kernel"; then
    echo "Configurando dispositivo..."
    sudo ./scripts/setup_device_robust.sh
fi

# Executa o programa com sudo usando o Python do venv
sudo PYTHONPATH="${PYTHONPATH}" "$PYTHON_BIN" src/main.py