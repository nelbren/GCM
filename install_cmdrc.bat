@echo off

REM install_cmdrc.bat - Crea o actualiza un acceso directo al CMD con cmdrc.bat cargado

powershell -ExecutionPolicy Bypass -NoProfile -Command "& '%~dp0install_cmdrc.ps1'"
