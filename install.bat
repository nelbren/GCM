@echo off
echo Ejecutando instalador GCM...

REM Verificar que Python esté disponible
call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no está instalado o no está en PATH.
    exit /b 1
)

REM Crear entorno virtual si no existe
if not exist .venv (
    echo 📦 Creando entorno virtual .venv...
    call python -m venv .venv
)

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Instalar requisitos dentro del entorno virtual
echo 🧪 Instalando requisitos dentro de .venv...
REM pip install --upgrade pip >nul
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Ejecutar configuración Python
python install.py

echo ✅ Instalación completa.