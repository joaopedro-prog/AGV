@echo off
setlocal
echo ======================================================================
echo          INICIANDO DASHBOARD WEB DO AGV (HMI E TELEMETRIA)
echo ======================================================================

REM Garante que o container principal esteja ativo
docker start meu_container_ros >nul 2>&1

REM Encerra eventuais instancias anteriores para evitar conflito de porta
docker rm -f agv_web_proxy >nul 2>&1
docker exec meu_container_ros pkill -f "dashboard_server" >nul 2>&1
docker exec meu_container_ros pkill -f "dashboard.launch.py" >nul 2>&1

REM Inicia ponte TCP na porta 8080 do Windows -> 172.17.0.1:8085 do container principal
echo Iniciando ponte HTTP/MJPEG (http://localhost:8080 para container:8085)...
docker run -d --rm --name agv_web_proxy -p 8080:8080 -v "%~dp0tcp_proxy.py:/tmp/tcp_proxy.py:ro" meu-agv:latest python3 /tmp/tcp_proxy.py 8080 172.17.0.1 8085 >nul

echo Abrindo o navegador em: http://localhost:8080
start http://localhost:8080

echo Iniciando servidor ROS 2 no container meu_container_ros...
docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh ros2 launch agv_dashboard dashboard.launch.py web_port:=8085
echo.
docker rm -f agv_web_proxy >nul 2>&1
pause
