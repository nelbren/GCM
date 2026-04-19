#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Running GCM installer for Unix..."

if ! command -v python >/dev/null 2>&1; then
    echo "❌ Python is not installed or is not in PATH."
    exit 1
fi

if [ ! -d "${SCRIPT_DIR}/.venv" ]; then
    echo "📦 Creating virtual environment .venv..."
    python -m venv "${SCRIPT_DIR}/.venv" || exit 1
fi

echo "🐍 Activating virtual environment .venv..."
if [ -r "${SCRIPT_DIR}/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.venv/bin/activate"
elif [ -r "${SCRIPT_DIR}/.venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.venv/Scripts/activate"
else
    echo "❌ Could not find the virtual environment activation script."
    exit 1
fi

echo "🧪 Installing requirements within .venv..."
python -m pip install --upgrade pip >/dev/null || exit 1
pip install -r "${SCRIPT_DIR}/requirements.txt" || exit 1

export MSYSTEM
export OSTYPE

python "${SCRIPT_DIR}/install.py" || exit 1

echo "✅ Complete installation."
