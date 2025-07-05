@echo off

set SCRIPT_DIR=%~dp0

REM Verifica que config.yml existe
if not exist %SCRIPT_DIR%config.yml (
    echo ❌ %SCRIPT_DIR%config.yml no encontrado. Aborta.
    exit /b 1
)

REM Verifica que Python esté disponible
call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado en el sistema.
    exit /b 1
)

REM Verifica entorno virtual
if not exist %HOMEPATH%\GCM\.venv\Scripts\python.exe (
    echo ❌ Entorno virtual .venv no encontrado. Ejecuta install.bat primero.
    exit /b 1
)

REM Verifica si secret.bat existe
if not exist %SCRIPT_DIR%secret.bat (
    echo ❌ %SCRIPT_DIR%secret.bat no encontrado. Aborta.
    exit /b 1
)
REM Fijar la Key
call %SCRIPT_DIR%secret.bat

REM Ejecutar GCM con entorno virtual
%SCRIPT_DIR%.venv\Scripts\python.exe %SCRIPT_DIR%gcm.py %*