@echo off

set SCRIPT_DIR=%~dp0

if exist %SCRIPT_DIR%apis\OpenRouter\secret.bat (
    echo 🔐 Setting Keys for OpenRouter Secret File...
    call %SCRIPT_DIR%apis\OpenRouter\secret.bat
)

if exist %SCRIPT_DIR%apis\OpenAI\secret.bat (
    echo 🔐 Setting Keys for OpenAI Secret File...
    call %SCRIPT_DIR%apis\OpenAI\secret.bat
)

if exist %SCRIPT_DIR%apis\Ollama\secret.bat (
    echo 🔐 Setting Keys for Ollama Secret File...
    call %SCRIPT_DIR%apis\Ollama\secret.bat
)