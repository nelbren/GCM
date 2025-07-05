#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$OSTYPE" == "cygwin" ]; then
    WIN_SCRIPT_DIR=$(cygpath -w "$SCRIPT_DIR")
    # incompatibilidad de terminales con input() de python
    # setup-x86_64.exe -P python 
fi

# Verifica existencia de config.yml
if [ ! -f "${SCRIPT_DIR}/config.yml" ]; then
    echo "❌ ${SCRIPT_DIR}/config.yml no encontrado. Aborta."
    exit 1
fi

# Verifica entorno virtual
if [ ! -f "${SCRIPT_DIR}/.venv/Scripts/python" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta install.bash primero."
    exit 1
fi

# Para que esten disponibles para gpm.py
export MSYSTEM
export OSTYPE

# Verifica existencia de secret.bash
if [ ! -f "${SCRIPT_DIR}/secret.bash" ]; then
    echo "❌ ${SCRIPT_DIR}/secret,bash no encontrado. Aborta."
    exit 1
fi

# Fijar la Key
source ${SCRIPT_DIR}/secret.bash

# Ejecuta el script usando el entorno virtual
if [ "$OSTYPE" == "cygwin" ]; then
    "$WIN_SCRIPT_DIR/.venv/Scripts/python.exe" "$WIN_SCRIPT_DIR/gcm.py" "$@"
else
    ${SCRIPT_DIR}/.venv/Scripts/python.exe "${SCRIPT_DIR}/gcm.py" "$@"
fi