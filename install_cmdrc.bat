@echo off

REM Create or update a CMD shortcut with cmdrc.bat loaded

powershell -ExecutionPolicy Bypass -NoProfile -Command "& '%~dp0install_cmdrc.ps1'"
