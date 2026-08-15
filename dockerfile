# 1. Usar a imagem com suporte completo a ferramentas de desktop (RViz/Gazebo)
FROM osrf/ros:humble-desktop-full

ARG DEBIAN_FRONTEND=noninteractive

# 2. Instalar ferramentas úteis combinando comandos para otimizar o cache do Docker
RUN apt-get update && apt-get install -y \
    build-essential \
    sudo \
    terminator \
    iproute2 \
    gedit \
    nano \
    wget \
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
    # Adicionar ao grupo dialout para permitir comunicação serial futura (ex: LiDAR, Arduino)
    && usermod -aG dialout $USERNAME

# 4. Mudar para o usuário não-root criado
USER $USERNAME
WORKDIR /workspace

# 5. Sourcing automático do ROS 2 no terminal do usuário
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc