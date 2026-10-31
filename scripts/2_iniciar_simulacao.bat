@echo off
setlocal
echo ======================================================================
echo  Iniciando SIMULACAO COMPLETA no Gazebo (Pista + Robo + Visao)...
echo ======================================================================
wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
start "Simulacao AGV - Gazebo" cmd /k "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true"
