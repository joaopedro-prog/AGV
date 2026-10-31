@echo off
setlocal
echo ======================================================================
echo  Iniciando visualizacao do robo no RViz 2...
echo ======================================================================
wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
start "RViz 2 - AGV" cmd /k "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 launch articubot_one view_robot.launch.py"
