@echo off
setlocal
cd /d "%~dp0.."
title Atualizar Projeto AGV

echo ======================================================================
echo          ATUALIZACAO AUTOMATICA DO PROJETO AGV (GITHUB + ROS 2)
echo ======================================================================
echo.

:: 1. Baixar atualizacoes do GitHub
echo [1/4] Baixando atualizacoes do GitHub...
git pull
if errorlevel 1 (
    echo.
    echo [AVISO] Falha ao rodar git pull. Verifique sua conexao com a internet.
    pause
    exit /b 1
)
echo Codigo atualizado com sucesso!
echo.

:: 2. Verificar se o Docker Desktop esta respondendo
echo [2/4] Verificando Docker no WSL...
wsl -d Ubuntu-24.04 docker info >nul 2>&1
if errorlevel 1 (
    echo [AVISO] O Docker nao esta respondendo no WSL.
    echo Certifique-se de que o Docker Desktop esta aberto com a luz verde no Windows
    echo e com a integracao Ubuntu-24.04 ativada em Settings - Resources - WSL Integration.
    echo.
    pause
    exit /b 1
)

:: 3. Construir imagem se necessario e iniciar container
echo [3/4] Garantindo imagem Docker e iniciando container...
wsl -d Ubuntu-24.04 docker compose up -d --build
if errorlevel 1 (
    echo [AVISO] Falha ao subir container com docker compose.
    pause
    exit /b 1
)
echo Container iniciado com sucesso!
echo.

:: 4. Compilar pacotes ROS 2 no workspace
echo [4/4] Compilando os pacotes ROS 2 (colcon build)...
wsl -d Ubuntu-24.04 docker exec -w /workspace meu_container_ros chmod +x /workspace/scripts/ros_exec.sh >nul 2>&1
wsl -d Ubuntu-24.04 docker exec -u 0 meu_container_ros chmod 777 /tmp/runtime-user >nul 2>&1
wsl -d Ubuntu-24.04 docker exec -w /workspace meu_container_ros /workspace/scripts/ros_exec.sh colcon build --symlink-install
if errorlevel 1 (
    echo [AVISO] Ocorreu um erro durante a compilacao.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   TUDO ATUALIZADO E PRONTO PARA RODAR!
echo   Basta dar dois cliques no "iniciar.bat" na raiz do projeto.
echo ======================================================================
echo.
pause
