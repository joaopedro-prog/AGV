@echo off
setlocal
echo Enviando comando STOP para o AGV parar...
wsl -d Ubuntu-24.04 docker exec meu_container_ros bash -c "sed -i 's/\r$//' /workspace/scripts/ros_exec.sh 2>/dev/null; chmod +x /workspace/scripts/ros_exec.sh 2>/dev/null" >nul 2>&1
wsl -d Ubuntu-24.04 docker exec meu_container_ros bash /workspace/scripts/ros_exec.sh ros2 run agv_brain agv_cmd stop
echo.
pause
