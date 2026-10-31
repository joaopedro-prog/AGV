@echo off
setlocal
echo ======================================================================
echo  Conectando ao terminal interativo do ROS 2...
echo ======================================================================
wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
start "Terminal ROS 2 - AGV" cmd /k "wsl -d Ubuntu-24.04 docker exec -it -w /workspace meu_container_ros bash"
