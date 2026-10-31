@echo off
setlocal
echo Compilando todos os pacotes com colcon build...
wsl -d Ubuntu-24.04 docker exec -w /workspace meu_container_ros /workspace/scripts/ros_exec.sh colcon build --symlink-install
echo.
echo Compilacao finalizada com sucesso!
echo.
pause
