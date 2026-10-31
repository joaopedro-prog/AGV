# 1. Usar a imagem com suporte completo a ferramentas de desktop (RViz/Gazebo)
FROM osrf/ros:humble-desktop-full

ARG DEBIAN_FRONTEND=noninteractive

# 2. Instalar ferramentas úteis e TODAS as dependências do robô de uma só vez
RUN apt-get update && apt-get install -y \
    build-essential \
    sudo \
    terminator \
    iproute2 \
    gedit \
    nano \
    wget \
    # Integração básica do Gazebo com ROS 2 (Resolve o erro 'gazebo_ros' not found)
    ros-humble-gazebo-ros-pkgs \
    # Multiplexador de comandos de velocidade (Resolve o erro 'twist_mux' not found)
    ros-humble-twist-mux \
    # Framework de controle e gerenciadores (Resolve o erro 'controller_manager' not found)
    ros-humble-controller-manager \
    ros-humble-ros2-control \
    ros-humble-ros2-controllers \
    # Plugin que conecta o ros2_control ao Gazebo (Essencial para criar o frame odom)
    ros-humble-gazebo-ros2-control \
    # Visão computacional (OpenCV + cv_bridge), Câmera USB Real (v4l2_camera) e Serial USB (pyserial)
    ros-humble-cv-bridge \
    ros-humble-v4l2-camera \
    ros-humble-rqt-image-view \
    ros-humble-joint-state-publisher-gui \
    python3-opencv \
    python3-serial \
    # Colcon é a ferramenta oficial para compilar workspaces ROS 2
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

# 3. Criar usuário não-root com UID/GID 1000 para evitar conflito de permissões no Windows/WSL
ARG USERNAME=user
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    # Adicionar privilégios de sudo sem necessidade de senha
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    # Adicionar aos grupos dialout e video para permitir comunicação serial USB e câmera USB
    && usermod -aG dialout,video $USERNAME

# 4. Mudar para o usuário não-root criado
USER $USERNAME
WORKDIR /workspace

# 5. Sourcing automático do ROS 2 no terminal do usuário
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
