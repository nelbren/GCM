@echo off
setlocal

call "%~dp0_cmd_utf8.bat" on

echo 🚀 Running GCM installer for Windows...

call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or is not in PATH.
    goto :fail
)

if not exist ".venv" (
    echo 📦 Creating virtual environment .venv...
    call python -m venv ".venv"
    if errorlevel 1 goto :fail
)

echo 🐍 Activating virtual environment .venv...
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

echo 🧪 Installing requirements within .venv...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
pip install -r requirements.txt
if errorlevel 1 goto :fail

python install.py
if errorlevel 1 goto :fail

echo ✅ Complete installation.
set "EXIT_CODE=0"
goto :end

:fail
set "EXIT_CODE=1"

:end
call "%~dp0_cmd_utf8.bat" off
endlocal & exit /b %EXIT_CODE%
