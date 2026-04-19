@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\..\_cmd_utf8.bat" on

pushd "%SCRIPT_DIR%" >nul
call "secret.bat"
"..\..\.venv\Scripts\python.exe" "query_model.py"
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

call "%SCRIPT_DIR%..\..\_cmd_utf8.bat" off
endlocal & exit /b %EXIT_CODE%
