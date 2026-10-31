#!/bin/bash
set -e

# Carrega o ambiente do ROS 2 Humble e os pacotes compilados do workspace
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
fi

if [ -f /workspace/install/setup.bash ]; then
    source /workspace/install/setup.bash
fi

# Executa o comando passado como argumento
exec "$@"
