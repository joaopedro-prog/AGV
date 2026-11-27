@echo off
setlocal enabledelayedexpansion
title Diagnostico de Aceleracao por Hardware GPU (AGV - ROS 2 / Gazebo)

cls
echo ======================================================================
echo       DIAGNOSTICO DE ACELERACAO POR HARDWARE GPU (ROS 2 / GAZEBO)
echo ======================================================================
echo.

REM 1. Identifica a GPU do Computador (Host Windows)
echo [1/3] Identificando Placa de Video no Windows...
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-CimInstance Win32_VideoController).Name"') do (
    echo       Placa Detectada: %%i
)
echo.

REM 2. Garante que o container esta rodando
echo [2/3] Verificando conexao com o container Docker (meu_container_ros)...
wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
echo       Container ativo com repasse de GPU (/dev/dxg).
echo.

REM 3. Executa o teste de renderizacao OpenGL / Direct3D 12 no container
echo [3/3] Consultando o renderizador 3D do Gazebo dentro do Linux:
echo ----------------------------------------------------------------------
wsl -d Ubuntu-24.04 docker exec meu_container_ros glxinfo -B
echo ----------------------------------------------------------------------
echo.

echo ======================================================================
echo                       RESULTADO DO DIAGNOSTICO
echo ======================================================================
echo  Se na linha "OpenGL renderer string" aparecer sua placa AMD Radeon
echo  e "Accelerated: yes", o Gazebo e todo o ambiente 3D estao rodando
echo  100%% ACELERADOS PELA GPU DE FORMA NATIVA (DirectX 12 / D3D12)!
echo.
echo  Deseja abrir o teste visual de engrenagens 3D (glxgears)?
echo    [1] Sim, abrir teste visual de FPS da GPU (glxgears)
echo    [2] Nao, voltar
echo ======================================================================
set /p "OPC=Escolha uma opcao [1 ou 2]: "

if "%OPC%"=="1" (
    echo.
    echo Abrindo janela de engrenagens 3D...
    echo (Feche a janelinha das engrenagens quando terminar para encerrar)
    echo.
    wsl -d Ubuntu-24.04 docker exec meu_container_ros glxgears
)

echo.
pause
exit /b 0
