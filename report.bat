@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%_cmd_utf8.bat" on

if not exist "%SCRIPT_DIR%config.yml" (
    echo ❌ "%SCRIPT_DIR%config.yml" not found. Abort.
    goto :fail
)

call python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found on the system.
    goto :fail
)

if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo ❌ Virtual environment .venv not found. Run install.bat first.
    goto :fail
)

if not exist "%SCRIPT_DIR%secret.bat" (
    echo ❌ "%SCRIPT_DIR%secret.bat" not found. Abort.
    goto :fail
)

call "%SCRIPT_DIR%secret.bat"
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%report_history.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
goto :end

:fail
set "EXIT_CODE=1"

:end
call "%SCRIPT_DIR%_cmd_utf8.bat" off
endlocal & exit /b %EXIT_CODE%
