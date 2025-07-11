@echo off

set SCRIPT_DIR=%~dp0

if not exist %SCRIPT_DIR%config.yml (
    echo ❌ %SCRIPT_DIR%config.yml not found. Abort.
    exit /b 1
)

call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found on the system.
    exit /b 1
)

if not exist %HOMEPATH%\GCM\.venv\Scripts\python.exe (
    echo ❌ Virtual environment .venv not found. Run install.bat first.
    exit /b 1
)

if not exist %SCRIPT_DIR%secret.bat (
    echo ❌ %SCRIPT_DIR%secret.bat not found. Abort.
    exit /b 1
)

call %SCRIPT_DIR%secret.bat

%SCRIPT_DIR%.venv\Scripts\python.exe %SCRIPT_DIR%gcm.py %*