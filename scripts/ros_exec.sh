#!/bin/bash
set -e

# Garante variaveis do servidor gráfico WSLg
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi
if [ -z "$WAYLAND_DISPLAY" ]; then
    export WAYLAND_DISPLAY=wayland-0
fi
if [ -z "$PULSE_SERVER" ]; then
    export PULSE_SERVER=unix:/mnt/wslg/PulseServer
fi
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR=/tmp/runtime-user
fi

# Driver de aceleracao por GPU nativo via WSLg Direct3D 12
export GALLIUM_DRIVER=d3d12
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH}

# Carrega o ambiente do Gazebo Classic e bibliotecas OGRE para prevencao de falhas de renderizacao
if [ -f /usr/share/gazebo/setup.sh ]; then
    source /usr/share/gazebo/setup.sh
elif [ -f /usr/share/gazebo-11/setup.sh ]; then
    source /usr/share/gazebo-11/setup.sh
fi

# Carrega o ambiente do ROS 2 Humble e os pacotes compilados do workspace
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
fi

if [ -f /workspace/install/setup.bash ]; then
    source /workspace/install/setup.bash
fi

# Paths para o Gazebo Classic encontrar modelos e malhas STL diretamente
export GAZEBO_MODEL_PATH=/workspace/install/articubot_one/share:/workspace/src:${GAZEBO_MODEL_PATH}
export GAZEBO_RESOURCE_PATH=/workspace/install/articubot_one/share:/workspace/src:${GAZEBO_RESOURCE_PATH}

# Executa o comando passado como argumento
exec "$@"
