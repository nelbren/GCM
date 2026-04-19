@echo off

if /i "%~1"=="on" goto :on
if /i "%~1"=="off" goto :off
exit /b 1

:on
for /f "tokens=2 delims=:." %%A in ('chcp') do set "_OLD_CP=%%A"
set "_OLD_CP=%_OLD_CP: =%"
chcp 65001 >nul
set PYTHONUTF8=1
exit /b 0

:off
if defined _OLD_CP chcp %_OLD_CP% >nul
exit /b 0
