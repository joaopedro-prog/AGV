@echo off
setlocal
title Comandos Rapidos do Gazebo (Hot-Reload, Luz e Teleporte)

wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1
wsl -d Ubuntu-24.04 docker exec -it meu_container_ros /workspace/scripts/ros_exec.sh python3 /workspace/scripts/gazebo_cmd.py

exit /b 0
