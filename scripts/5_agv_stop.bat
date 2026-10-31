@echo off
setlocal
echo Enviando comando STOP para o AGV parar...
wsl -d Ubuntu-24.04 docker exec meu_container_ros /workspace/scripts/ros_exec.sh ros2 run agv_brain agv_cmd stop
echo.
pause
