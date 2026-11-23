@echo off
setlocal
echo Enviando comando START para o AGV seguir a linha...
wsl -d Ubuntu-24.04 docker exec meu_container_ros bash -c "sed -i 's/\r$//' /workspace/scripts/ros_exec.sh 2>/dev/null; chmod +x /workspace/scripts/ros_exec.sh 2>/dev/null" >nul 2>&1
wsl -d Ubuntu-24.04 docker exec meu_container_ros bash /workspace/scripts/ros_exec.sh ros2 run agv_brain agv_cmd start
echo.
pause
