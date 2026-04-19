@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%..\..\_cmd_utf8.bat" on

call "%SCRIPT_DIR%secret.bat"
set "DEBUG=True"
call "%SCRIPT_DIR%list.bat"
if errorlevel 1 goto :fail
call "%SCRIPT_DIR%test.bat"
set "EXIT_CODE=%ERRORLEVEL%"
goto :end

:fail
set "EXIT_CODE=1"

:end
call "%SCRIPT_DIR%..\..\_cmd_utf8.bat" off
endlocal & exit /b %EXIT_CODE%
