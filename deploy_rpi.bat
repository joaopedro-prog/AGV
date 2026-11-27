@echo off
setlocal
echo ======================================================================
echo   ELETRON AGV - DEPLOY ESTILO FRC PARA RASPBERRY PI (1 CLIQUE)
echo ======================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\rpi\agv_deploy.ps1" %*
echo.
pause
