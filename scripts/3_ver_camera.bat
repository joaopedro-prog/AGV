@echo off
setlocal
echo ======================================================================
echo  Abrindo visualizador da camera do AGV...
echo ======================================================================
wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
wsl -d Ubuntu-24.04 docker exec meu_container_ros bash -c "sed -i 's/\r$//' /workspace/scripts/ros_exec.sh 2>/dev/null; chmod +x /workspace/scripts/ros_exec.sh 2>/dev/null" >nul 2>&1
start "Camera AGV - Visao" cmd /k "wsl -d Ubuntu-24.04 docker exec -it meu_container_ros bash /workspace/scripts/ros_exec.sh ros2 run rqt_image_view rqt_image_view /agv/line_debug_image"
