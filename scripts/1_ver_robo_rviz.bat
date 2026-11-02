@echo off
setlocal
title Visualizacao do AGV no RViz 2 (Simulacao e Sensores)

echo ======================================================================
echo  Iniciando RViz 2 com Odometria, Lidar 360 e Animacao das Rodas...
echo  (Fixed Frame: odom ^| Sincronizado com tempo simulado do Gazebo)
echo ======================================================================

wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
start "RViz 2 - AGV (Odometria e Lidar)" cmd /k "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 launch articubot_one view_robot.launch.py use_sim_time:=true"
