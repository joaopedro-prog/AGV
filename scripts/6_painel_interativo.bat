@echo off
setlocal
echo Abrindo painel de controle interativo do AGV...
wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
start "Painel AGV" cmd /k "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 run agv_brain agv_cmd"
