@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

if exist "%SCRIPT_DIR%apis\OpenRouter\secret.bat" (
    call :print_info "Setting Keys for OpenRouter Secret File..."
    call "%SCRIPT_DIR%apis\OpenRouter\secret.bat"
)

if exist "%SCRIPT_DIR%apis\OpenAI\secret.bat" (
    call :print_info "Setting Keys for OpenAI Secret File..."
    call "%SCRIPT_DIR%apis\OpenAI\secret.bat"
)

if exist "%SCRIPT_DIR%apis\Ollama\secret.bat" (
    call :print_info "Setting Keys for Ollama Secret File..."
    call "%SCRIPT_DIR%apis\Ollama\secret.bat"
)

endlocal
exit /b 0

:print_info
powershell -NoProfile -Command "Write-Host ([char]::ConvertFromUtf32(0x1F510) + ' ' + $args[0])" -- %~1
exit /b 0
