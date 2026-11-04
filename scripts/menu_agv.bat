@echo off
setlocal
cd /d "%~dp0"
title AGV - Painel Principal

:MENU
cls
echo ======================================================================
echo                     PAINEL DE CONTROLE DO AGV (ROS 2)
echo ======================================================================
echo.
echo   [1] Abrir Terminal Interativo ROS 2 (bash dentro do container)
echo   [2] Visualizar Robo no RViz 2 (Odometria, Rodas e Pista)
echo   [3] Iniciar SIMULACAO COMPLETA no Gazebo (Pista + Robo + Visao)
echo   [4] Ver Camera e Deteccao de Linha (rqt_image_view)
echo.
echo   -------------------------- COMANDOS DO AGV -------------------------
echo   [5] Mandar o Robo SEGUIR A LINHA (START)
echo   [6] Mandar o Robo PARAR IMEDIATAMENTE (STOP)
echo   [7] Abrir Painel Interativo de Missoes (agv_cmd)
echo.
echo   -------------------------- FERRAMENTAS -----------------------------
echo   [8] Recompilar o Workspace (colcon build)
echo   [9] Baixar Atualizacoes do GitHub (git pull + docker + build)
echo   [U] Subir Atualizacoes para o GitHub (git add + commit + push)
echo   [G] Testar e Verificar Aceleracao da GPU (AMD / D3D12)
echo   [Z] Comandos Rapidos do Gazebo (Janela Externa: Hot-Reload, Luz, Teleporte)
echo   [0] Sair
echo ======================================================================
choice /C 123456789GZU0 /N /M "Digite a opcao: "

if errorlevel 13 goto SAIR
if errorlevel 12 goto CMD_PUSH
if errorlevel 11 goto CMD_GAZEBO
if errorlevel 10 goto CMD_GPU
if errorlevel 9 goto CMD_UPDATE
if errorlevel 8 goto CMD_BUILD
if errorlevel 7 goto CMD_PANEL
if errorlevel 6 goto CMD_STOP
if errorlevel 5 goto CMD_START
if errorlevel 4 goto CMD_CAM
if errorlevel 3 goto CMD_SIM
if errorlevel 2 goto CMD_RVIZ
if errorlevel 1 goto CMD_TERMINAL
goto MENU

:CMD_TERMINAL
call entrar_container.bat
goto MENU

:CMD_RVIZ
call 1_ver_robo_rviz.bat
goto MENU

:CMD_SIM
call 2_iniciar_simulacao.bat
goto MENU

:CMD_CAM
call 3_ver_camera.bat
goto MENU

:CMD_START
call 4_agv_start.bat
goto MENU

:CMD_STOP
call 5_agv_stop.bat
goto MENU

:CMD_PANEL
call 6_painel_interativo.bat
goto MENU

:CMD_BUILD
call compilar.bat
goto MENU

:CMD_UPDATE
call atualizar_projeto.bat
goto MENU

:CMD_PUSH
call subir_atualizacoes.bat
goto MENU

:CMD_GPU
call verificar_gpu.bat
goto MENU

:CMD_GAZEBO
call 7_menu_gazebo.bat
goto MENU

:SAIR
exit /b 0
