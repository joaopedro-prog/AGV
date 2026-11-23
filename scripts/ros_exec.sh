#!/bin/bash
set -e

# 1. Garante variaveis do servidor grafico WSLg
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

# 2. Corrige permissoes de diretorios graficos, socket X11 e dispositivo GPU (/dev/dxg)
sudo mkdir -p /tmp/runtime-user 2>/dev/null || true
sudo chmod 777 /tmp/runtime-user 2>/dev/null || true
if [ -e /dev/dxg ]; then
    sudo chmod 666 /dev/dxg 2>/dev/null || true
fi
if [ ! -S /tmp/.X11-unix/X0 ] && [ -S /mnt/wslg/.X11-unix/X0 ]; then
    sudo mkdir -p /tmp/.X11-unix 2>/dev/null || true
    sudo ln -sf /mnt/wslg/.X11-unix/X0 /tmp/.X11-unix/X0 2>/dev/null || true
fi

# 3. Auto-deteccao inteligente de GPU:
# Tenta usar aceleracao por hardware Direct3D 12 (WSLg). Se a maquina nao suportar D3D12
# ou se /usr/lib/wsl/lib nao estiver montado, faz fallback automatico para OpenGL Software (llvmpipe)
# evitando que o gzclient crashe com "failed to create drisw screen" (exit code -11).
USE_D3D12=0
if [ -e /dev/dxg ] && [ -f /usr/lib/wsl/lib/libd3d12.so ]; then
    export GALLIUM_DRIVER=d3d12
    export LIBGL_ALWAYS_SOFTWARE=0
    export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH}

    if python3 -c "
import ctypes, sys
try:
    x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
    gl = ctypes.cdll.LoadLibrary('libGL.so.1')
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    gl.glXGetFBConfigs.restype = ctypes.c_void_p
    gl.glXGetFBConfigs.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    dpy = x11.XOpenDisplay(None)
    if not dpy:
        sys.exit(0)
    n = ctypes.c_int(0)
    cfg = gl.glXGetFBConfigs(dpy, 0, ctypes.byref(n))
    sys.exit(0 if (cfg and n.value > 0) else 1)
except Exception:
    sys.exit(0)
" 2>/dev/null; then
        USE_D3D12=1
    fi
fi

if [ "$USE_D3D12" -eq 0 ]; then
    export GALLIUM_DRIVER=llvmpipe
    export LIBGL_ALWAYS_SOFTWARE=1
fi

# 4. Carrega o ambiente do Gazebo Classic e bibliotecas OGRE para prevencao de falhas de renderizacao
if [ -f /usr/share/gazebo/setup.sh ]; then
    source /usr/share/gazebo/setup.sh
elif [ -f /usr/share/gazebo-11/setup.sh ]; then
    source /usr/share/gazebo-11/setup.sh
fi

# 5. Carrega o ambiente do ROS 2 Humble e os pacotes compilados do workspace
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
fi

if [ -f /workspace/install/setup.bash ]; then
    source /workspace/install/setup.bash
fi

# 6. Paths para o Gazebo Classic encontrar modelos e malhas STL diretamente
export GAZEBO_MODEL_PATH=/workspace/install/articubot_one/share:/workspace/src:${GAZEBO_MODEL_PATH}
export GAZEBO_RESOURCE_PATH=/workspace/install/articubot_one/share:/workspace/src:${GAZEBO_RESOURCE_PATH}

# Executa o comando passado como argumento
exec "$@"
