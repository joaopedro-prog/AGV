#!/bin/bash
set -e

# Força aceleração direta por Hardware GPU (Mesa D3D12 vGPU via WSLg)
export LIBGL_ALWAYS_SOFTWARE=0
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH}
export OGRE_RTT_MODE=FBO

# Carrega o ambiente do ROS 2 Humble e os pacotes compilados do workspace
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
fi

if [ -f /workspace/install/setup.bash ]; then
    source /workspace/install/setup.bash
fi

# Executa o comando passado como argumento
exec "$@"
