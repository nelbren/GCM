#!/bin/bash
echo "🚀 Ejecutando instalador GCM para Unix..."

# Verifica que Python esté disponible
if ! command -v python &> /dev/null; then
    echo "❌ Python no está instalado."
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "📦 Creando entorno virtual..."
    python -m venv .venv
fi

# Activar entorno virtual e instalar requisitos
echo "🧪 Instalando requisitos..."
source .venv/Scripts/activate
# pip install --upgrade pip > /dev/null
python -m pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# Para que esten disponibles para install.py
export MSYSTEM
export OSTYPE

# Ejecutar configuración
python install.py

echo "✅ Instalación completa."
