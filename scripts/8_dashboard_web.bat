@echo off
setlocal
title AGV - Dashboard Web

echo ======================================================================
echo             INICIANDO DASHBOARD WEB DO AGV (ROS 2)
echo ======================================================================
echo.
echo 1. Garantindo que o container Docker esta ativo...
wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1

echo 2. Iniciando servidor HTTP e streaming em segundo plano (porta 5000)...
start "AGV Web Dashboard Server" /min cmd /k "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 run agv_brain web_dashboard"

echo 3. Aguardando servidor inicializar...
timeout /t 2 /nobreak >nul

echo 4. Abrindo o Dashboard Web no navegador padrao...
start http://localhost:5000

echo.
echo ======================================================================
echo   DASHBOARD WEB PRONTO!
echo   Acesse em: http://localhost:5000
echo   (Tambem pode ser acessado na rede Wi-Fi via celular/tablet)
echo ======================================================================
echo.
timeout /t 3 >nul
