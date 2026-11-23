@echo off
setlocal
echo Compilando todos os pacotes com colcon build...
wsl -d Ubuntu-24.04 docker exec -w /workspace meu_container_ros bash -c "sed -i 's/\r$//' /workspace/scripts/ros_exec.sh 2>/dev/null; chmod +x /workspace/scripts/ros_exec.sh 2>/dev/null" >nul 2>&1
wsl -d Ubuntu-24.04 docker exec -w /workspace meu_container_ros bash /workspace/scripts/ros_exec.sh colcon build --symlink-install
echo.
echo Compilacao finalizada com sucesso!
echo.
pause
