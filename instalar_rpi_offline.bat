@echo off
setlocal
echo ======================================================================
echo   ELETRON AGV - INSTALACAO INICIAL OFFLINE NA RASPBERRY PI (ARM64)
echo ======================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\rpi\setup_offline_rpi.ps1" %*
echo.
pause
