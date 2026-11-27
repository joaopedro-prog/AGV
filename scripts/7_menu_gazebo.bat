@echo off
setlocal
echo Abrindo janela externa de Comandos Rapidos do Gazebo...

wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
start "Comandos Rapidos do Gazebo" cmd /c "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh python3 /workspace/scripts/gazebo_cmd.py"

exit /b 0
