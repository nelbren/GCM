#!/bin/bash

echo "🚀 Running GCM installer for Unix..."

if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or is not in PATH."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment .venv..."
    python -m venv .venv
fi

echo "🐍 Activating virtual environment .venv..."
[ -r .venv/Scripts/activate ] && source .venv/Scripts/activate
[ -r .venv/bin/activate ] && source .venv/bin/activate

echo "🧪 Installing requirements within .venv..."
python -m pip install --upgrade pip > /dev/null
pip install -r requirements.txt

export MSYSTEM # To be available for: install.py
export OSTYPE  # To be available for: install.py

python install.py

echo "✅ Complete installation."
