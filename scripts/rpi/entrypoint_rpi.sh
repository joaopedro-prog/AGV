#!/bin/bash
set -e

source /opt/ros/humble/setup.bash
if [ -f /workspace/install/setup.bash ]; then
    source /workspace/install/setup.bash
fi

ENABLE_CAMERA="${ENABLE_CAMERA:-true}"
ENABLE_LIDAR="${ENABLE_LIDAR:-false}"
LIDAR_PORT="${LIDAR_PORT:-/dev/agv_lidar}"
ENABLE_DASHBOARD="${ENABLE_DASHBOARD:-true}"
WEB_PORT="${WEB_PORT:-8080}"
AUTO_START="${AUTO_START:-false}"

echo "======================================================================"
echo "  ELETRON AGV // RUNTIME EMBARCADO RASPBERRY PI 3B (SEM SIMULACAO)"
echo "======================================================================"
echo "  Camera V4L2 : ${ENABLE_CAMERA}"
echo "  RPLIDAR A1  : ${ENABLE_LIDAR} (${LIDAR_PORT})"
echo "  Dashboard   : ${ENABLE_DASHBOARD} (porta ${WEB_PORT})"
echo "  Auto Start  : ${AUTO_START}"
echo "======================================================================"

# Inicia receptor de joystick UDP (porta 9876) em segundo plano
python3 /workspace/scripts/teleop_joy_receiver.py &
TELEOP_PID=$!

cleanup() {
    echo "[entrypoint_rpi] Encerrando processos do AGV com seguranca..."
    kill -TERM "${TELEOP_PID}" 2>/dev/null || true
    if [ -n "${ROS_PID}" ]; then
        kill -TERM "${ROS_PID}" 2>/dev/null || true
        wait "${ROS_PID}" 2>/dev/null || true
    fi
}
trap cleanup SIGTERM SIGINT

ros2 launch agv_hardware agv_complete.launch.py \
    sim_mode:=false \
    auto_start:="${AUTO_START}" \
    enable_camera:="${ENABLE_CAMERA}" \
    enable_lidar:="${ENABLE_LIDAR}" \
    lidar_port:="${LIDAR_PORT}" \
    enable_dashboard:="${ENABLE_DASHBOARD}" \
    web_port:="${WEB_PORT}" &
ROS_PID=$!

wait "${ROS_PID}"
