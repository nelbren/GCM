@echo off

echo 🚀 Running GCM installer for Windows....

call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or is not in PATH.
    exit /b 1
)

if not exist .venv (
    echo 📦 Creating virtual environment .venv...
    call python -m venv .venv
)

echo 🐍 Activating virtual environment .venv...
call .venv\Scripts\activate.bat

echo 🧪 Installing requirements within .venv...
python -m pip install --upgrade pip
pip install -r requirements.txt

python install.py

echo ✅ Complete installation.