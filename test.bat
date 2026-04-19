@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%_cmd_utf8.bat" on

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%test_runner.py"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :end
)

echo ⚠️ Virtual environment .venv not found. Falling back to system Python.
python "%SCRIPT_DIR%test_runner.py"
set "EXIT_CODE=%ERRORLEVEL%"

:end
call "%SCRIPT_DIR%_cmd_utf8.bat" off
endlocal & exit /b %EXIT_CODE%
