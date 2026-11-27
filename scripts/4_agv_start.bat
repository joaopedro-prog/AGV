@echo off
setlocal
echo Enviando comando START para o AGV seguir a linha...
wsl -d Ubuntu-24.04 docker exec meu_container_ros /workspace/scripts/ros_exec.sh ros2 run agv_brain agv_cmd start
echo.
pause
