@echo off
setlocal
echo ======================================================================
echo          INICIANDO DASHBOARD WEB DO AGV (HMI & TELEMETRIA)
echo ======================================================================
echo Abrindo o navegador em: http://localhost:8080
start http://localhost:8080

echo Iniciando servidor no container ROS 2...
wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 launch agv_dashboard dashboard.launch.py web_port:=8080
echo.
pause
