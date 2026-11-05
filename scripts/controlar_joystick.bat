@echo off
setlocal
cd /d "%~dp0"
title AGV - Teleoperacao por Joystick USB

echo ======================================================================
echo                CONTROLE TELEOPERADO POR JOYSTICK USB - AGV
echo ======================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao foi encontrado no PATH do Windows!
    echo Instale o Python ou adicione ao PATH.
    pause
    exit /b 1
)

python -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo [+] Instalando biblioteca pygame necessaria para leitura USB...
    pip install pygame
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar pygame.
        pause
        exit /b 1
    )
)

python "%~dp0controlar_joystick.py"

if errorlevel 1 (
    echo.
    echo [!] Ocorreu um erro ou a operacao foi interrompida.
    pause
)
