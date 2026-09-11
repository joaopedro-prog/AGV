# AGV Simulation Environment

Ambiente de desenvolvimento e simulação do AGV utilizando:

* Windows 10/11
* WSL 2
* Ubuntu
* Docker Desktop
* Docker Compose
* ROS 2 Humble
* Gazebo
* RViz2
* WSLg
* GPU via D3D12

O objetivo deste ambiente é permitir o desenvolvimento e teste do robô em simulação antes da execução no hardware real.

A arquitetura foi projetada para que os mesmos conceitos e interfaces ROS 2 possam ser utilizados posteriormente no Raspberry Pi 5 do robô.

---

# 1. Arquitetura

```text
┌───────────────────────────────────────────────┐
│                  Windows                      │
│                                               │
│  Windows Terminal / PowerShell               │
│                                               │
│  GPU AMD                                      │
│      │                                        │
└──────┼────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────────────────┐
│                    WSL 2                      │
│                                               │
│  Ubuntu                                       │
│                                               │
│  WSLg                                         │
│    │                                          │
│    └── D3D12 / GPU                            │
│                                               │
│  Docker CLI                                   │
│    │                                          │
└────┼──────────────────────────────────────────┘
     │
     ▼
┌───────────────────────────────────────────────┐
│               Docker Desktop                  │
│                                               │
│  Container: meu_container_ros                 │
│                                               │
│  ├── ROS 2 Humble                              │
│  ├── Gazebo                                    │
│  ├── RViz2                                     │
│  ├── ros2_control                              │
│  ├── ROS 2 packages                            │
│  └── /workspace                               │
│                                               │
│  GPU                                           │
│  └── /dev/dxg → D3D12 → GPU                   │
└───────────────────────────────────────────────┘
```

---

# 2. Pré-requisitos

O computador precisa possuir:

* Windows 10 versão 21H2 ou superior, ou Windows 11
* Virtualização habilitada na BIOS/UEFI
* WSL 2
* Ubuntu
* Docker Desktop
* Driver de GPU compatível com WSL
* Git

Para aplicativos GUI Linux no WSL, a Microsoft utiliza uma GPU virtual (vGPU) para aceleração de OpenGL.

Para Docker Desktop, o backend WSL 2 é o ambiente recomendado para containers Linux no Windows.

---

# 3. Instalação do WSL

Abra o **PowerShell como Administrador**.

Verifique se o WSL está instalado:

```powershell
wsl --version
```

Atualize o WSL:

```powershell
wsl --update
```

Verifique as distribuições instaladas:

```powershell
wsl --list --verbose
```

A distribuição utilizada pelo projeto deve estar rodando em:

```text
VERSION 2
```

Exemplo:

```text
NAME            STATE       VERSION
Ubuntu-24.04    Stopped     2
```

Caso a distribuição esteja utilizando WSL 1:

```powershell
wsl --set-version Ubuntu-24.04 2
```

---

# 4. Verificar suporte à GPU no WSL

Entre no Ubuntu:

```powershell
wsl -d Ubuntu-24.04
```

Dentro do Ubuntu:

```bash
ls -l /dev/dxg
```

Deve existir:

```text
/dev/dxg
```

Esse dispositivo é utilizado pelo WSL para disponibilizar a GPU virtual para aplicações Linux.

Também é possível verificar as bibliotecas:

```bash
ls /usr/lib/wsl/lib/
```

Devem existir bibliotecas como:

```text
libd3d12.so
libd3d12core.so
libdxcore.so
```

---

# 5. Configurar aceleração gráfica no WSL

Instale as ferramentas de teste:

```bash
sudo apt update
sudo apt install -y mesa-utils
```

Execute:

```bash
glxinfo -B
```

O resultado deve indicar uma GPU real/virtual acelerada.

Exemplo:

```text
OpenGL vendor string: Microsoft Corporation
OpenGL renderer string: D3D12 (AMD Radeon RX 580 2048SP)
Accelerated: yes
```

### Importante

Não instalar drivers AMD Linux dentro do WSL para esse propósito.

No WSL, a GPU é disponibilizada através da camada de virtualização gráfica do Windows/D3D12.

---

# 6. Configurar o Docker Desktop

Instale o Docker Desktop no Windows.

Durante a configuração, utilize o backend:

```text
WSL 2
```

Depois de instalar, abra o Docker Desktop e certifique-se de que ele está funcionando.

No Ubuntu:

```bash
docker --version
```

Teste:

```bash
docker run hello-world
```

Se aparecer a mensagem de sucesso do `hello-world`, o Docker está funcionando.

---

# 7. Permissão do Docker no Ubuntu

Caso apareça:

```text
permission denied while trying to connect to the Docker daemon
```

execute:

```bash
sudo usermod -aG docker $USER
```

Depois saia do WSL:

```bash
exit
```

No PowerShell:

```powershell
wsl --shutdown
```

Abra novamente:

```powershell
wsl -d Ubuntu-24.04
```

Teste:

```bash
docker run hello-world
```

---

# 8. Clonar o projeto

O projeto foi desenvolvido para ser independente da localização do repositório.

Clone o repositório normalmente:

```bash
git clone <URL_DO_REPOSITORIO>
```

Entre na pasta:

```bash
cd <PASTA_DO_REPOSITORIO>
```

Exemplo:

```bash
git clone https://github.com/usuario/AGV.git
cd AGV
```

> O caminho da pasta pode ser diferente em cada computador. Nenhum caminho absoluto do Windows deve ser necessário.

---

# 9. Estrutura esperada

A raiz do projeto deve conter algo semelhante a:

```text
AGV/
│
├── Dockerfile
├── docker-compose.yml
├── README.md
│
├── src/
│   └── ...
│
├── launch/
│   └── ...
│
├── description/
│   └── ...
│
└── ...
```

A estrutura poderá evoluir conforme o desenvolvimento do robô.

---

# 10. Dockerfile

O projeto utiliza ROS 2 Humble através da imagem:

```dockerfile
FROM osrf/ros:humble-desktop-full
```

O ambiente contém as principais ferramentas necessárias para a simulação:

* ROS 2 Humble
* Gazebo
* RViz2
* gazebo_ros
* ros2_control
* ros2_controllers
* controller_manager
* gazebo_ros2_control
* twist_mux
* colcon

---

# 11. Configuração da GPU no Docker

Para aplicativos gráficos dentro de containers no WSLg, é necessário disponibilizar os recursos gráficos do WSL ao container.

O WSLg documenta três elementos principais para acesso à vGPU:

```text
/dev/dxg
/usr/lib/wsl
LD_LIBRARY_PATH=/usr/lib/wsl/lib
```

Além disso, para aplicações gráficas, o container precisa acessar os recursos do WSLg.

O `docker-compose.yml` deve conter uma configuração semelhante a:

```yaml
services:

  ros_sim:

    build:
      context: .
      dockerfile: Dockerfile

    image: meu-agv:latest

    container_name: meu_container_ros

    stdin_open: true
    tty: true

    network_mode: host
    ipc: host

    environment:
      - DISPLAY=${DISPLAY}
      - WAYLAND_DISPLAY=${WAYLAND_DISPLAY}
      - XDG_RUNTIME_DIR=/tmp/runtime-user
      - PULSE_SERVER=${PULSE_SERVER}

      - QT_X11_NO_MITSHM=1

      # D3D12 / WSL GPU
      - GALLIUM_DRIVER=d3d12
      - LD_LIBRARY_PATH=/usr/lib/wsl/lib

    volumes:

      # Workspace do projeto
      - .:/workspace

      # X11
      - /tmp/.X11-unix:/tmp/.X11-unix:rw

      # WSLg
      - /mnt/wslg:/mnt/wslg

      # Wayland
      - ${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}:/tmp/runtime-user/${WAYLAND_DISPLAY}

      # Bibliotecas da GPU do WSL
      - /usr/lib/wsl:/usr/lib/wsl

    devices:

      # WSL virtual GPU
      - /dev/dxg:/dev/dxg
```

---

# 12. Construir a imagem

Na raiz do repositório:

```bash
docker compose build
```

Ou:

```bash
docker compose up -d --build
```

A imagem será criada com:

```text
meu-agv:latest
```

---

# 13. Iniciar o ambiente

Na raiz do projeto:

```bash
docker compose up -d
```

Verifique:

```bash
docker ps
```

Deve aparecer:

```text
meu_container_ros
```

---

# 14. Entrar no container

Execute:

```bash
docker exec -it meu_container_ros bash
```

O terminal deverá ficar semelhante a:

```text
user@docker-desktop:/workspace$
```

O diretório:

```text
/workspace
```

corresponde à raiz do repositório.

---

# 15. Testar a GPU dentro do container

Dentro do container:

```bash
glxinfo -B
```

Se `glxinfo` não estiver instalado:

```bash
sudo apt update
sudo apt install -y mesa-utils
```

Depois:

```bash
glxinfo -B
```

O resultado esperado é semelhante a:

```text
OpenGL vendor string: Microsoft Corporation
OpenGL renderer string: D3D12 (AMD Radeon RX 580 2048SP)
Accelerated: yes
```

### Resultado correto

```text
Device: D3D12 (AMD Radeon RX 580 2048SP)
Accelerated: yes
```

Isso confirma:

```text
Windows
   ↓
WSL 2
   ↓
WSLg
   ↓
Docker
   ↓
/dev/dxg
   ↓
D3D12
   ↓
GPU
```

Em vez de:

```text
OpenGL renderer string: llvmpipe
```

`llvmpipe` significa renderização por software/CPU e não é o resultado desejado para o ambiente de simulação.

---

# 16. Testar o Gazebo

Dentro do container:

```bash
gazebo
```

O Gazebo deverá abrir uma janela no Windows.

Se a janela abrir e a GPU estiver reportando:

```text
Accelerated: yes
```

a aceleração gráfica está funcionando.

---

# 17. Testar o RViz2

Abra outra aba do Windows Terminal.

Entre no WSL:

```powershell
wsl -d Ubuntu-24.04
```

Entre no mesmo container:

```bash
docker exec -it meu_container_ros bash
```

Execute:

```bash
rviz2
```

O RViz2 deverá abrir através do WSLg.

---

# 18. Utilizar vários terminais

Não é necessário criar vários containers.

Todos os processos podem utilizar o mesmo container.

Exemplo:

```text
Windows Terminal
│
├── Aba 1
│   └── meu_container_ros
│       └── Gazebo
│
├── Aba 2
│   └── meu_container_ros
│       └── RViz2
│
├── Aba 3
│   └── meu_container_ros
│       └── ROS 2 nodes
│
└── Aba 4
    └── meu_container_ros
        └── Debug / comandos
```

Em cada nova aba:

```bash
docker exec -it meu_container_ros bash
```

---

# 19. Comandos ROS 2

Dentro do container:

### Listar nós

```bash
ros2 node list
```

### Listar tópicos

```bash
ros2 topic list
```

### Ver informações de um tópico

```bash
ros2 topic info /cmd_vel
```

### Ver mensagens

```bash
ros2 topic echo /cmd_vel
```

### Listar serviços

```bash
ros2 service list
```

### Listar parâmetros

```bash
ros2 param list
```

---

# 20. Executar o projeto

Quando os pacotes do AGV estiverem implementados, os launch files poderão ser executados diretamente dentro do container.

Exemplo:

```bash
ros2 launch <pacote> <arquivo>.launch.py
```

A arquitetura pretendida é:

```text
ROS 2
 │
 ├── Robot Description
 │
 ├── Gazebo
 │    ├── Chassis
 │    ├── Wheels
 │    ├── LiDAR
 │    ├── Camera
 │    └── Sensors
 │
 ├── ros2_control
 │
 ├── Controllers
 │
 ├── Odometry
 │
 ├── TF
 │
 └── Navigation
```

---

# 21. Simulação x Robô real

O objetivo é manter interfaces ROS 2 semelhantes entre simulação e hardware.

```text
                 ROS 2
                   │
          ┌────────┴────────┐
          │                 │
       SIMULAÇÃO          ROBÔ REAL
          │                 │
       Gazebo           Raspberry Pi 5
          │                 │
   Sensores virtuais   Sensores reais
          │                 │
          └────────┬────────┘
                   │
              ROS 2 Topics
```

Exemplos:

```text
/cmd_vel
/odom
/scan
/image_raw
/tf
/tf_static
```

Isso permite desenvolver algoritmos na simulação antes de transferi-los para o robô físico.

---

# 22. Quando reconstruir a imagem

Não é necessário executar:

```bash
docker compose build
```

toda vez.

Reconstrua quando houver alterações no:

```text
Dockerfile
```

ou quando novas dependências forem adicionadas.

Para reconstruir:

```bash
docker compose build
```

Depois:

```bash
docker compose up -d
```

Ou diretamente:

```bash
docker compose up -d --build
```

---

# 23. Quando apenas iniciar

Se nada relacionado ao Dockerfile mudou:

```bash
docker compose up -d
```

Não é necessário reconstruir a imagem.

---

# 24. Parar o ambiente

Para parar o container:

```bash
docker compose down
```

Isso remove o container, mas não remove a imagem Docker.

A imagem:

```text
meu-agv:latest
```

continua disponível.

---

# 25. Rotina diária

Depois que o ambiente já estiver configurado, o fluxo normal é:

### 1. Abrir Ubuntu

```powershell
wsl -d Ubuntu-24.04
```

### 2. Entrar na pasta do repositório

```bash
cd <PASTA_DO_REPOSITORIO>
```

### 3. Iniciar Docker

```bash
docker compose up -d
```

### 4. Abrir um terminal no container

```bash
docker exec -it meu_container_ros bash
```

### 5. Abrir outros terminais conforme necessário

```bash
docker exec -it meu_container_ros bash
```

### 6. Executar:

```text
Gazebo
RViz2
ROS 2 nodes
Launch files
Debug
```

---

# 26. Checklist de GPU

Caso Gazebo/RViz estejam lentos ou utilizando CPU excessivamente:

### WSL

```bash
ls -l /dev/dxg
```

Deve existir:

```text
/dev/dxg
```

### Bibliotecas

```bash
ls /usr/lib/wsl/lib/
```

Verifique se existem:

```text
libd3d12.so
libd3d12core.so
libdxcore.so
```

### WSL OpenGL

```bash
glxinfo -B
```

Esperado:

```text
D3D12 (GPU)
Accelerated: yes
```

### Container

Entre no container:

```bash
docker exec -it meu_container_ros bash
```

Depois:

```bash
glxinfo -B
```

Esperado:

```text
D3D12 (GPU)
Accelerated: yes
```

Se aparecer:

```text
llvmpipe
```

a renderização está acontecendo por software e a configuração de GPU precisa ser revisada.

---

# 27. Diagnóstico rápido

## Problema: Docker não conecta

```bash
docker run hello-world
```

Se houver erro de permissão:

```bash
sudo usermod -aG docker $USER
```

Depois:

```bash
exit
```

No PowerShell:

```powershell
wsl --shutdown
```

Abra novamente o Ubuntu.

---

## Problema: `/dev/dxg` não existe

No WSL:

```bash
ls -l /dev/dxg
```

Se não existir:

1. Atualize o WSL:

```powershell
wsl --update
```

2. Reinicie o WSL:

```powershell
wsl --shutdown
```

3. Verifique novamente.

---

## Problema: container usa `llvmpipe`

Dentro do container:

```bash
glxinfo -B
```

Se aparecer:

```text
OpenGL renderer string: llvmpipe
```

verifique:

```bash
echo $LD_LIBRARY_PATH
```

Deve conter:

```text
/usr/lib/wsl/lib
```

Verifique:

```bash
ls /usr/lib/wsl/lib/
```

E:

```bash
ls -l /dev/dxg
```

---

# 28. Princípio do ambiente

Este projeto utiliza Docker principalmente para garantir que:

```text
ROS 2
Gazebo
RViz2
Dependências
Pacotes
Ferramentas
```

sejam reproduzíveis entre diferentes computadores.

O caminho do projeto no Windows **não é fixo**.

O Docker Compose utiliza:

```yaml
- .:/workspace
```

onde `.` representa a raiz do repositório atual.

Portanto, o projeto pode estar em:

```text
C:\Projetos\AGV
```

ou:

```text
D:\Git\AGV
```

ou em qualquer outra localização.

O procedimento continua sendo:

```bash
cd <PASTA_DO_REPOSITORIO>
docker compose up -d
```

---

# 29. Resumo dos comandos

## Primeira configuração

```powershell
wsl --update
wsl --list --verbose
```

No Ubuntu:

```bash
ls -l /dev/dxg
ls /usr/lib/wsl/lib/
```

Teste:

```bash
sudo apt update
sudo apt install -y mesa-utils
glxinfo -B
```

Docker:

```bash
docker run hello-world
```

Projeto:

```bash
git clone <URL_DO_REPOSITORIO>
cd <PASTA_DO_REPOSITORIO>
docker compose up -d --build
```

Teste do container:

```bash
docker exec -it meu_container_ros bash
```

Dentro:

```bash
glxinfo -B
```

Esperado:

```text
D3D12 (GPU)
Accelerated: yes
```

---

# 30. Rotina normal

```bash
cd <PASTA_DO_REPOSITORIO>
```

```bash
docker compose up -d
```

```bash
docker exec -it meu_container_ros bash
```

E em outras abas:

```bash
docker exec -it meu_container_ros bash
```

Para finalizar:

```bash
docker compose down
```

---

## Resultado esperado

Ao final da configuração, o ambiente deverá possuir:

```text
Windows
   │
   ▼
WSL 2
   │
   ├── Ubuntu
   │
   ├── WSLg
   │     └── GPU acelerada
   │
   ▼
Docker Desktop
   │
   ▼
ROS 2 Humble Container
   │
   ├── Gazebo
   ├── RViz2
   ├── ros2_control
   ├── AGV simulation
   │
   └── GPU
        └── D3D12
             └── AMD GPU
```

O objetivo final é utilizar este ambiente como base para desenvolver, testar e validar o software do AGV em simulação antes da implementação no robô físico.

## Para rodar o ROS2

1. **Garanta que está na raiz do seu workspace:**

```
cd /workspace

```

2. **Compile o workspace:**

```
colcon build --symlink-install

```

3. **Carregue o ambiente local:**

```
source install/setup.bash

```

Agora o ROS 2 reconhecerá todos os seus pacotes locais