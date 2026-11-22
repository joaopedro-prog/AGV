# ELETRON AGV — Autonomous Mobile Robot (ROS 2 Humble)

Ambiente completo de desenvolvimento, simulação física de alta fidelidade e operação embarcada para o **Robô Móvel Autônomo (AGV / AMR ELETRON)** utilizando **ROS 2 Humble**, **Gazebo Classic**, **RViz 2** e integração com **Docker + WSL 2 (Windows 10/11 com aceleração de GPU via Direct3D 12)**, além de container de produção enxuto (**ARM64 Headless sem simulação**) para **Raspberry Pi 3 Model B + ESP32 DevKit V1 + 2× REV Spark MAX + 2× Motores CIM 2.5"**.

---

## 📑 Sumário

1. [Visão Geral e Arquitetura](#1-visão-geral-e-arquitetura)
2. [Descrição CAD do Robô Real (Física e Materiais)](#2-descrição-cad-do-robô-real-física-e-materiais)
3. [Estrutura de Pastas e Pacotes](#3-estrutura-de-pastas-e-pacotes)
4. [Como Executar no Dia a Dia (Menu Interativo)](#4-como-executar-no-dia-a-dia-menu-interativo)
5. [Controle de Versão pelo Menu (Baixar e Subir para o GitHub)](#5-controle-de-versão-pelo-menu-baixar-e-subir-para-o-github)
6. [Comandos Rápidos do Gazebo (Janela Externa)](#6-comandos-rápidos-do-gazebo-janela-externa)
7. [Mundos e Circuitos no Gazebo](#7-mundos-e-circuitos-no-gazebo)
8. [Aceleração por GPU e Otimização de Desempenho (60 FPS)](#8-aceleração-por-gpu-e-otimização-de-desempenho-60-fps)
9. [Sensores e Atuadores (Câmera, 2× Ultrassônicos, IMU e Relés)](#9-sensores-e-atuadores-câmera-2-ultrassônicos-imu-e-relés)
10. [Simulação (PC) vs. Robô Real (Docker ARM64 na Raspberry Pi 3B)](#10-simulação-pc-vs-robô-real-docker-arm64-na-raspberry-pi-3b)
11. [Orquestração do Seguidor de Linha (START / STOP)](#11-orquestração-do-seguidor-de-linha-start--stop)
12. [Teleoperação por Joystick USB (Simulação e Robô Real)](#12-teleoperação-por-joystick-usb-simulação-e-robô-real)
13. [Dashboard Web Cockpit (Vídeo MJPEG, Sonar Dual, IMU e HMI Wi-Fi)](#13-dashboard-web-cockpit-vídeo-mjpeg-sonar-dual-imu-e-hmi-wi-fi)
14. [Arquitetura Elétrica KiCad Rev 2.0 & Implantação no Robô Físico](#14-arquitetura-elétrica-kicad-rev-20--implantação-no-robô-físico)
15. [Configuração Inicial do Ambiente (PC / Notebook Novo)](#15-configuração-inicial-do-ambiente-pc--notebook-novo)
16. [Solução de Problemas Comuns (Troubleshooting)](#16-solução-de-problemas-comuns-troubleshooting)

---

## 1. Visão Geral e Arquitetura

O projeto foi projetado com uma separação clara entre **hardware físico**, **simulação gráfica** e **camada de inteligência**:

```text
                       [ CÂMERA CSI / USB V4L2 ]              [ ESP32 DevKit V1 ]
                                   │                                  ▲  (2x Spark MAX PWM 50Hz, 2x KY-040 20:1,
                                   │ /dev/video0                      │   2x HC-SR04 Frontais, E-Stop GPIO 33)
┌──────────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────────┐
│ RASPBERRY PI 3B (REAL) / DOCKER  ▼                                  ▼  UART 115200 bps (CRC16-CCITT, 30 Hz)   │
│                          [v4l2_camera_node]                [serial_bridge_node]        [rpi_sensors_node]      │
│                                  │                                  ▲  │ /agv/ultrasonic_*    │ /imu/data_raw  │
│                                  │ /camera/image_raw                │  │ /odom                │ Relés K1 / K2  │
│                                  ▼                                  │  ▼                      ▼                │
│                         [line_detector_node]                        │ [agv_dashboard_node :8080]               │
│                        (OpenCV ROI: acha a fita)                    │ (Stream MJPEG + Sonar + IMU + Comandos)  │
│                                  │                                  │                                          │
│                                  │ /agv/line_error                  │ /diff_cont/cmd_vel_unstamped             │
│                                  ▼                                  │                                          │
│                      [line_follower_node (PID)] ───► [twist_mux] ───┘                                          │
│                                                           ▲                                                    │
│                                                           │ /cmd_vel_joy (Prio 100) / /cmd_vel_emergency (255) │
│                                                  [teleop_joy_receiver :9876 UDP]                               │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Principais Características
* **Independência de Ambiente:** Os mesmos nós de visão, controle e Dashboard funcionam tanto no Gazebo quanto na Raspberry Pi 3B sem alterar o código-fonte.
* **Modelo CAD Real Integrado:** Malhas 3D exportadas diretamente do Fusion 360 com propriedades físicas calculadas por densidade real (Alumínio 6061-T6 e Poliuretano).
* **Tração Diferencial Confiável:** Rodas motrizes com contato esférico de precisão; 4 rodízios passivos (rodas bobas) com folga calibrada anti-tombamento de $3\text{ mm}$ para garantir tração máxima sem perda de contato normal.
* **Aceleração Gráfica por Hardware (PC) e Imagem ARM64 Enxuta (RPi 3B):** Suporte a D3D12/WSLg no Windows para o Gazebo e `Dockerfile.rpi` headless (~800 MB, sem simulação) na Raspberry Pi 3B.
* **Segurança NR-12 e Watchdog 200 ms:** Corte imediato em `1500 µs` nos Spark MAX em caso de emergência física ou perda serial, com procedimento formal de rearme em 5 passos.

---

## 2. Descrição CAD do Robô Real (Física e Materiais)

O modelo 3D reflete a geometria exata do robô real construído no Autodesk Fusion 360:

| Componente | Material Real | Densidade Adotada | Massa Calculada | Função Dinâmica |
| :--- | :--- | :--- | :--- | :--- |
| **Chassis Principal** | Alumínio estrutural | $2700\text{ kg/m}^3$ | $\approx 9.19\text{ kg}$ | Estrutura de suporte, baterias e eletrônica |
| **Roda Esquerda (`left_wheel`)** | Poliuretano (PU) | $1200\text{ kg/m}^3$ | $\approx 0.22\text{ kg}$ | Roda motriz tracionada esquerda ($\varnothing = 0.1524\text{ m}$) |
| **Roda Direita (`right_wheel`)** | Poliuretano (PU) | $1200\text{ kg/m}^3$ | $\approx 0.22\text{ kg}$ | Roda motriz tracionada direita ($\varnothing = 0.1524\text{ m}$) |
| **4 Rodízios (`FL, FR, BL, BR`)** | Placa/suporte Al + roda PU | Misto | $\approx 17.7\text{ g}$ cada | Rodas bobas passivas de apoio e estabilidade |
| **Massa Total da Estrutura** | — | — | **$\approx 9.75\text{ kg}$** | Centro de gravidade rebaixado para estabilidade |

> [!IMPORTANT]
> **Dinâmica de Rodagem:** Apenas a roda esquerda e a roda direita são tracionadas pelo plugin diferencial (`libgazebo_ros_diff_drive.so`). Os 4 rodízios nos cantos são **rodas bobas passivas** com atrito nulo ($\mu = 0.001$) e folga vertical de segurança de $3\text{ mm}$, garantindo que $100\%$ do peso do AGV repouse sobre as rodas tracionadas.

---

## 3. Estrutura de Pastas e Pacotes

```text
AGV/
├── .gitignore                    # Arquivos ignorados pelo Git (build, install, log, temporários)
├── dockerfile                    # Imagem Desktop Completa (PC / Gazebo / RViz 2 / WSLg D3D12)
├── docker-compose.yml            # Orquestrador PC com repasse de GPU D3D12 e volumes
├── Dockerfile.rpi                # Imagem ARM64 Headless Enxuta para Raspberry Pi 3B (SEM Gazebo/RViz)
├── docker-compose.rpi.yml        # Orquestrador de Produção na Raspberry Pi 3B (auto-restart no boot)
├── iniciar.bat                   # [ATALHO PRINCIPAL] Menu interativo no Windows
├── controlar_joystick.bat        # Atalho de teleoperação por Joystick USB (Local ou Wi-Fi UDP)
├── README.md                     # Documentação completa do projeto
│
├── docs/                         # Contratos Formais e Documentação de Engenharia Elétrica
│   ├── contracts/
│   │   ├── protocolo_serial_esp32_rpi.md          # Framing, CRC16-CCITT, Watchdog 200ms
│   │   ├── catalogo_topicos_e_servicos_ros2.md    # Tópicos, QoS e Prioridades do twist_mux
│   │   └── maquina_estados_seguranca.md           # 3 Níveis de Parada e Procedimento de Rearme
│   └── hardware/
│       ├── guia_implantacao_robo_fisico.md        # Passo a passo KiCad Rev 2.0, RPi 3B e calibração
│       ├── circuito_potencia.md                   # Memorial descritivo e dimensionamento elétrico 12V
│       ├── circuito_potencia_agv.drawio           # Esquemático editável no Draw.io / Diagrams.net
│       └── circuito_potencia_agv.svg              # Esquemático vetorial em alta resolução
│
├── firmware/                     # Firmware do Microcontrolador
│   └── agv_mcu_firmware/
│       └── agv_mcu_firmware.ino  # Firmware C++ ESP32 (2x Spark MAX PWM 50Hz, 2x KY-040 20:1, 2x HC-SR04, CRC16)
│
├── scripts/                      # Scripts de automação Windows (.bat), Linux (.sh) e Raspberry Pi
│   ├── rpi/
│   │   ├── setup_rpi.sh          # Instalador automático da RPi 3B (Swap 2GB, I2C, UART0, CSI, udev, Docker)
│   │   ├── entrypoint_rpi.sh     # Entrypoint de produção (Teleop UDP :9876 + Bringup Real + Dashboard :8080)
│   │   └── 99-agv-devices.rules  # Regras udev persistentes (/dev/agv_esp32, /dev/agv_cam, GPIO, I2C)
│   ├── menu_agv.bat              # Menu interativo do AGV
│   ├── 1_ver_robo_rviz.bat       # Abre o RViz 2 com robô real, odometria, rodas e pista
│   ├── 2_iniciar_simulacao.bat   # Abre o Gazebo com seletor de mundos e robô
│   ├── 3_ver_camera.bat          # Monitor visual da detecção de linha (rqt_image_view)
│   ├── 4_agv_start.bat           # Manda o AGV começar a seguir linha (START)
│   ├── 5_agv_stop.bat            # Manda o AGV parar imediatamente (STOP)
│   ├── 6_painel_interativo.bat   # Painel CLI de missões do AGV
│   ├── 7_menu_gazebo.bat         # Menu de comandos rápidos do Gazebo em janela dedicada
│   ├── 8_abrir_dashboard.bat     # Abre o Cockpit Web HMI em http://localhost:8080 (com ponte TCP automática)
│   ├── tcp_proxy.py              # Ponte TCP leve para expor a porta do container no localhost do Windows
│   ├── teleop_joy_receiver.py    # Receptor ROS 2 de Joystick (Pipe local ou Socket UDP :9876 via Wi-Fi)
│   ├── gazebo_cmd.py             # Script backend Python para hot-reload, iluminação e teleporte
│   ├── subir_atualizacoes.bat    # Envia alterações locais para o GitHub (add + commit + push)
│   ├── atualizar_projeto.bat     # Baixa atualizações do GitHub (git pull + docker + build)
│   ├── verificar_gpu.bat         # Diagnóstico de GPU e teste visual de FPS (glxgears)
│   ├── compilar.bat              # Executa colcon build no workspace
│   ├── entrar_container.bat      # Abre um terminal bash direto dentro do container
│   └── ros_exec.sh               # Intermediador oficial Linux para carregar o ambiente ROS 2
│
├── src/                          # Código-fonte ROS 2 (4 Pacotes Principais)
│   ├── articubot_one/            # [PACOTE 1] Modelagem 3D CAD, URDF/Xacro e Mundos Gazebo
│   │   ├── description/          # Arquivos Xacro (robot_core, camera, ultrasonic dual frontal)
│   │   ├── meshes/               # 16 malhas STL reais do robô exportadas do Fusion 360
│   │   ├── launch/               # Launches de simulação (launch_sim, view_robot, rsp)
│   │   └── worlds/               # Circuitos de simulação (armazem_logistico, pista_completa_plana, etc.)
│   │
│   ├── agv_hardware/             # [PACOTE 2] Ponte de Hardware Real e Orquestração
│   │   ├── agv_hardware/         # serial_bridge_node (ESP32 UART/USB) e rpi_sensors_node (Relés K1/K2 + MPU6050)
│   │   ├── config/               # hardware_params.yaml (portas, KY-040 800 ticks/rev, câmera 320x240@15fps)
│   │   └── launch/               # agv_complete.launch.py e hardware_bringup.launch.py
│   │
│   ├── agv_brain/                # [PACOTE 3] Inteligência, Visão Computacional e PID
│   │   ├── agv_brain/            # line_detector_node (OpenCV ROI) e line_follower_node (PID + 2x Ultrassônicos)
│   │   ├── config/               # brain_params.yaml (ganhos PID, velocidades, cor da linha)
│   │   └── launch/               # brain.launch.py (detecção + seguidor de linha)
│   │
│   └── agv_dashboard/            # [PACOTE 4] Dashboard Web, Stream MJPEG, Sonar Dual, IMU e HMI
│       ├── agv_dashboard/        # dashboard_node.py (Servidor HTTP Multi-Thread + Stream MJPEG + REST)
│       ├── static/               # index.html (Cockpit Industrial Responsivo)
│       └── launch/               # dashboard.launch.py (Launch do Servidor Web)
│
├── tiles/                        # Modelos 3D modulares de pista (tile-reta, curva, rampa)
└── worlds/                       # Pasta espelhada de circuitos do Gazebo
```

---

## 4. Como Executar no Dia a Dia (Menu Interativo)

Na raiz do projeto no Windows, basta dar **dois cliques em `iniciar.bat`**.

O menu interativo será exibido:

```text
======================================================================
                    PAINEL DE CONTROLE DO AGV (ROS 2)
======================================================================

  [1] Abrir Terminal Interativo ROS 2 (bash dentro do container)
  [2] Visualizar Robo no RViz 2 (Odometria, Rodas e Pista)
  [3] Iniciar SIMULACAO COMPLETA no Gazebo (Pista + Robo + Visao)
  [4] Ver Camera e Deteccao de Linha (rqt_image_view)

  -------------------------- COMANDOS DO AGV -------------------------
  [5] Mandar o Robo SEGUIR A LINHA (START)
  [6] Mandar o Robo PARAR IMEDIATAMENTE (STOP)
  [7] Abrir Painel Interativo de Missoes (agv_cmd)
  [J] Controlar Robo por JOYSTICK USB (Simulado ou Real)
  [W] Abrir DASHBOARD WEB no Navegador (Telemetria, HMI e Video)

  -------------------------- FERRAMENTAS -----------------------------
  [8] Recompilar o Workspace (colcon build)
  [9] Baixar Atualizacoes do GitHub (git pull + docker + build)
  [U] Subir Atualizacoes para o GitHub (git add + commit + push)
  [G] Testar e Verificar Aceleracao da GPU (AMD / D3D12)
  [Z] Comandos Rapidos do Gazebo (Janela Externa: Hot-Reload, Luz, Teleporte)
  [0] Sair
======================================================================
Digite a opcao:
```

---

## 5. Controle de Versão pelo Menu (Baixar e Subir para o GitHub)

O painel de controle oferece integração completa com o Git em duas vias:

### Opção `[9]`: Baixar Atualizações (`atualizar_projeto.bat`)
* Executa `git pull` para trazer as últimas novidades da nuvem.
* Valida a integridade do container Docker.
* Reconstrói e recompila automaticamente todos os pacotes ROS 2 com `colcon build`.

### Opção `[U]`: Subir Atualizações (`subir_atualizacoes.bat`)
* Exibe o status de todos os arquivos modificados.
* Solicita uma mensagem explicativa para o commit (ou gera automaticamente com carimbo de data/hora se pressionar ENTER).
* Executa `git add -A`, grava o `git commit` e envia para o repositório remoto.

---

## 6. Comandos Rápidos do Gazebo (Janela Externa)

Ao digitar **`[Z]`** no menu principal, uma janela externa de comandos rápidos é aberta e pode permanecer minimizada ao lado do Gazebo:

* **[1] Hot-Reload do Robô:** Atualiza o modelo do robô no Gazebo na hora, sem precisar fechar e reabrir a simulação.
* **[2] Teleportar para a Largada:** Reposiciona o AGV sobre a linha de partida.
* **[3] Teleportar para a Rampa:** Coloca o AGV imediatamente antes da subida da rampa 3D para testes de inclinação.
* **[4] Pausar / Despausar Simulação:** Congela ou retoma a física do mundo.
* **[5] Resetar Física do Mundo:** Zera o relógio e restaura as posições iniciais.
* **[6] Controle de Iluminação Solar:** Alterna entre iluminação Diurna Clara, Suave, Entardecer ou Penumbra Noturna.

---

## 7. Mundos e Circuitos no Gazebo

Os circuitos do Gazebo foram redimensionados para a escala **$4.0\times$** (tiles de $1.20\text{ m} \times 1.20\text{ m}$, raio de curvatura de $0.60\text{ m}$), mantendo a proporção ideal para a bitola de $0.468\text{ m}$ e comprimento de $0.70\text{ m}$ do robô real:

| Mundo | Descrição | Destaques |
| :--- | :--- | :--- |
| **`armazem_logistico.world`** | ★ **Armazém Fabril / Estoque com Gôndolas** | Galpão industrial com paredes, docas de carga, 4 blocos de gôndolas porta-paletes, circuito cíclico de linha contínua e **5 marcações coloridas de estações** para fusão com odometria. |
| **`pista_completa_plana.world`** | Pista Plana Completa com Bypass | 32 tiles escalados ($1.20\text{ m}$), curvas amplas ($R=0.60\text{ m}$), retas de alta velocidade e rotatória central. |
| **`pista_teste_8_tiles.world`** | Circuito Compacto de Teste | 8 tiles ($3.6\times 3.6\text{ m}$, $R=0.60\text{ m}$), ideal para validação ágil do algoritmo PID e testes de visão. |

### Estações e Marcadores de Cores no `armazem_logistico.world`

| Estação / Setor | Cor Gazebo | Código RGB | Coordenadas $(X, Y)$ | Ação e Significado no Processo |
| :--- | :--- | :--- | :--- | :--- |
| **Estação 1: Doca de Entrada** | `Gazebo/Green` | `#00E676` (Verde) | $(X = -2.40, Y = 3.00)$ | Ponto de partida (Spawn) e recebimento/abastecimento de carga |
| **Estação 2: Picking Estoque A** | `Gazebo/Blue` | `#2979FF` (Azul) | $(X = 4.20, Y = 1.20)$ | Coleta de itens e insumos no bloco de gôndolas A |
| **Estação 3: Interseção Central** | `Gazebo/Turquoise` | `#00E5FF` (Ciano) | $(X = 0.00, Y = 0.00)$ | Verificação de tráfego, decisão de rota e bypass |
| **Estação 4: Picking Estoque B** | `Gazebo/Yellow` | `#FFEA00` (Amarelo) | $(X = 0.00, Y = -3.00)$ | Coleta de itens e insumos no bloco de gôndolas B |
| **Estação 5: Doca de Expedição** | `Gazebo/Red` | `#FF1744` (Vermelho) | $(X = -4.20, Y = -0.60)$ | Descarga final de material expedido |

---

## 8. Aceleração por GPU e Otimização de Desempenho (60 FPS)

O ambiente de simulação no PC utiliza repasse direto de hardware via WSLg (`/dev/dxg` e `GALLIUM_DRIVER=d3d12`), comunicando-se nativamente com sua GPU (**AMD Radeon** ou **NVIDIA GeForce**).

### Como Verificar a Aceleração
1. Abra o menu `iniciar.bat` e escolha **`G`** (ou dê duplo clique em `scripts/verificar_gpu.bat`).
2. O script identifica a placa de vídeo no Windows e exibe os dados do Linux (`Device: D3D12`, `Accelerated: yes`).

---

## 9. Sensores e Atuadores (Câmera, 2× Ultrassônicos, IMU e Relés)

O robô utiliza exclusivamente o conjunto de sensores e atuadores definido no **Esquemático Oficial KiCad Rev 2.0** (sem LiDAR):

### 1. Câmera Inferior de Rastreamento (Pi Camera CSI / USB V4L2)
* **Arquivo:** [`src/articubot_one/description/camera.xacro`](src/articubot_one/description/camera.xacro)
* **Posição:** Integrada à abertura inferior do chassi ($x = 0.2557\text{ m}, z = 0.0704\text{ m}$), apontada para o piso à frente do robô.
* **Tópicos:** `/camera/image_raw` (`320×240 @ 15 FPS` na RPi 3B) e HUD de visão em `/agv/line_debug_image`.

### 2. 2× Sensores Ultrassônicos Frontais (`HC-SR04` Esquerdo e Direito)
* **Arquivo:** [`src/articubot_one/description/ultrasonic.xacro`](src/articubot_one/description/ultrasonic.xacro)
* **Posição:** Montados lado a lado no para-choque frontal ($x = 0.355\text{ m}, y = \pm 0.120\text{ m}, z = 0.060\text{ m}$).
* **Pinos ESP32:** `TRIG_SHARED` no `GPIO 27` (disparo não-bloqueante a 10 Hz); `ECHO1_3V3` (Esquerdo) no `GPIO 26` e `ECHO2_3V3` (Direito) no `GPIO 25` com divisor resistivo `1k/2k`.
* **Tópicos:** `/agv/ultrasonic_left` e `/agv/ultrasonic_right` (`sensor_msgs/msg/Range`, alcance $0.03\text{ m}$ a $3.00\text{ m}$).

### 3. IMU 6-DOF (`MPU6050` via Barramento I2C da Raspberry Pi 3B)
* **Nó:** [`src/agv_hardware/agv_hardware/rpi_sensors_node.py`](src/agv_hardware/agv_hardware/rpi_sensors_node.py)
* **Ligação:** Pinos `BCM 2 (SDA1)` e `BCM 3 (SCL1)` da Raspberry Pi 3B (`/dev/i2c-1`, endereço `0x68`).
* **Tópico:** `/imu/data_raw` (`sensor_msgs/msg/Imu`: aceleração linear em $\text{m/s}^2$ e velocidade angular em $\text{rad/s}$).

### 4. Relés de Potência 12V (`K1` Ventoinhas e `K2` Fita LED 5050)
* **Relé K1 (`BCM GPIO 17` / Pino 11 RPi):** Aciona as duas ventoinhas de arrefecimento 12V (`Fan #1` e `Fan #2`).
* **Relé K2 (`BCM GPIO 27` / Pino 13 RPi):** Aciona a fita LED 5050 12V (acesa contínua em operação normal e piscante em parada remota ou emergência).

---

## 10. Simulação (PC) vs. Robô Real (Docker ARM64 na Raspberry Pi 3B)

O arquivo mestre [`src/agv_hardware/launch/agv_complete.launch.py`](src/agv_hardware/launch/agv_complete.launch.py) orquestra todo o sistema através do argumento `sim_mode`, enquanto a infraestrutura Docker é separada entre PC e Raspberry Pi:

### A) Modo Simulação (No PC com Gazebo + GPU WSLg)
Usa [`dockerfile`](dockerfile) + [`docker-compose.yml`](docker-compose.yml):
```bash
ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true world:=armazem_logistico.world
```
* Sobe o Gazebo Classic com o mundo selecionado e spawna o robô CAD com física diferencial e os 2 sensores ultrassônicos frontais simulados.
* O robô inicia sempre no estado seguro `IDLE` (parado).

### B) Modo Robô Físico Real (Na Raspberry Pi 3B — Sem Simulação)
Usa [`Dockerfile.rpi`](Dockerfile.rpi) + [`docker-compose.rpi.yml`](docker-compose.rpi.yml):
* **Imagem Enxuta (`ros:humble-ros-base-jammy` ARM64):** Não instala Gazebo, RViz 2, X11 nem bibliotecas de GPU WSL2 (~800 MB em vez de ~4 GB).
* **Inicialização Automática no Boot (`restart: unless-stopped`):** Ao energizar a bateria de 12V, o container `agv_eletron_real` sobe sozinho via [`scripts/rpi/entrypoint_rpi.sh`](scripts/rpi/entrypoint_rpi.sh) iniciando:
  1. `teleop_joy_receiver.py` (escutando Joystick Wi-Fi na porta UDP `9876`).
  2. `serial_bridge` (protocolo CRC16-CCITT a 30 Hz com o ESP32 em `/dev/agv_esp32` ou `/dev/serial0`).
  3. `rpi_sensors` (controle dos relés `K1`/`K2` e leitura I2C do `MPU6050`).
  4. `v4l2_camera` (câmera CSI/USB em `320×240 @ 15 FPS`).
  5. `agv_brain` (`line_detector` + `line_follower`) e `agv_dashboard` (porta HTTP `8080`).

---

## 11. Orquestração do Seguidor de Linha (START / STOP)

Por segurança, o robô **sempre inicia parado** no estado `IDLE`. Ele só começa a seguir linha quando você autorizar.

Você pode enviar comandos de três formas:

1. **Pelo Dashboard Web (`http://localhost:8080` ou `http://<IP_DA_RPI>:8080`):**
   * Botões **▶ INICIAR (START)**, **⏹ PARAR (STOP)**, **🚨 EMERGÊNCIA (E-STOP)** e **🔄 REARMAR SISTEMA (RESET)**.
2. **Pelo Menu Interativo / Atalhos:**
   * Opção `[5]` no menu (ou `scripts/4_agv_start.bat`) $\rightarrow$ Inicia o movimento (**START**).
   * Opção `[6]` no menu (ou `scripts/5_agv_stop.bat`) $\rightarrow$ Para imediatamente (**STOP**).
3. **Pelo Terminal CLI do ROS 2:**
   ```bash
   ros2 run agv_brain agv_cmd start
   ros2 run agv_brain agv_cmd stop
   ```

---

## 12. Teleoperação por Joystick USB (Simulação e Robô Real)

O sistema conta com suporte completo para controle manual por **Joystick / Gamepad USB** (Xbox, PlayStation DualShock/DualSense ou genéricos USB).

* **Simulação Local (Gazebo / Docker):** Transmissão via pipe direto para `teleop_joy_receiver.py` dentro do container.
* **Robô Físico Real (Wi-Fi):** Envio de pacotes via socket UDP (porta `9876`) diretamente para o IP da Raspberry Pi 3B pela rede Wi-Fi.
* **Prioridade Absoluta via `twist_mux`:** Publica em `/cmd_vel_joy` com **prioridade 100**, sobrepondo o seguidor de linha autônomo (prioridade 30).

---

## 13. Dashboard Web Cockpit (Vídeo MJPEG, Sonar Dual, IMU e HMI Wi-Fi)

O AGV conta com um painel de controle industrial responsivo servido diretamente pelo nó `agv_dashboard` (`ThreadingHTTPServer`), acessível em qualquer navegador no Windows ou celular via Wi-Fi sem depender de multicast DDS do ROS 2:
* **Na Simulação (PC Windows):** `http://localhost:8080` (iniciado via opção **`[W]`** do menu ou [`scripts/8_abrir_dashboard.bat`](scripts/8_abrir_dashboard.bat), que levanta automaticamente a ponte TCP [`scripts/tcp_proxy.py`](scripts/tcp_proxy.py)).
* **No Robô Físico (Raspberry Pi 3B):** `http://<IP_DA_RPI>:8080` (sobe automaticamente no boot).

### Destaques e Funcionalidades:
* **Stream de Vídeo MJPEG ao Vivo (`/api/camera_stream`):** Transmite na própria porta `8080` a visão em tempo real com alternância em 1 clique entre **HUD Linha (`/agv/line_debug_image`)** e **Câmera Crua (`/camera/image_raw`)**.
* **Visão Gráfica dos 2× Sensores Ultrassônicos Frontais (`<canvas>`):** Desenha os cones acústicos dos sensores **US1 Esquerdo (`GPIO 26`)** e **US2 Direito (`GPIO 25`)**, linha vermelha de alerta em `0.25 m` e leituras digitais em metros e centímetros.
* **Telemetria 6-DOF do IMU MPU6050 (`/imu/data_raw`):** Exibe status `ONLINE`/`OFFLINE`, aceleração linear ($a_x, a_y, a_z$ em $\text{m/s}^2$) e giroscópio ($\omega_x, \omega_y$ e taxa de giro Yaw em $^\circ/\text{s}$).
* **Banner de Segurança e Estados:**
  * 🔵 **`IDLE` / `STOP_CONFIRMED`:** Robô em standby seguro ou parada concluída.
  * 🟢 **`EM_MOVIMENTO`:** Navegação autônoma ativa seguindo linha.
  * 🟡 **`REMOTE_STOP_REQUESTED`:** Desaceleração controlada em rampa.
  * 🔴 **`HARDWARE_ESTOP_ACTIVE`:** Emergência física (`BTN_E_STOP` no `GPIO 33`), Watchdog de `200 ms` ou E-STOP acionado.
  * 🟠 **`RECOVERY_PENDING`:** Botão físico destravado, pronto para rearme pelo botão **🔄 REARMAR SISTEMA (RESET)**.

---

## 14. Arquitetura Elétrica KiCad Rev 2.0 & Implantação no Robô Físico

O guia completo de fiação, gravação do ESP32, provisionamento da Raspberry Pi 3B e calibração em cavalete está documentado em:  
👉 **[`docs/hardware/guia_implantacao_robo_fisico.md`](docs/hardware/guia_implantacao_robo_fisico.md)**

### Resumo do Hardware Real (KiCad Rev 2.0):
* **Potência 12V:** Bateria `MK ES17-12 (12V 18Ah)` $\rightarrow$ Fusível Principal `100A (8 AWG)` $\rightarrow$ Chave Geral `QG-01` $\rightarrow$ Caixa de Fusíveis `XF-01` (`F1/F2 = 40A` Spark MAX + Motores CIM 2.5", `F3 = 5A` Step-Down `XL4015 5.1V/5A`, `F4 = 5A` Relés `K1` Ventoinhas e `K2` Fita LED 5050).
* **Controladores de Motor (ESP32 $\rightarrow$ 2× REV Spark MAX):** Sinal Servo PWM 50 Hz (`1000–2000 µs`, `1500 µs` neutro em 16-bit LEDC) nos pinos **`GPIO 13` (`PWM_LEFT`)** e **`GPIO 14` (`PWM_RIGHT`)**.
* **Encoders em Redução 20:1 (2× KY-040 = `800 ticks/volta`):**
  * `ENC1` (Esquerdo): `CLK = GPIO 34`, `DT = GPIO 35`
  * `ENC2` (Direito): `CLK = GPIO 39 (VN)`, `DT = GPIO 36 (VP)`
* **2× Ultrassônicos Frontais (`HC-SR04` com divisor 1k/2k):** `TRIG_SHARED = GPIO 27`, `ECHO1_3V3 (Esq) = GPIO 26`, `ECHO2_3V3 (Dir) = GPIO 25`.
* **Emergência e UART:** `BTN_E_STOP` no `GPIO 33` (`INPUT_PULLUP`); comunicação `115200 bps` espelhada simultaneamente em `Serial` (USB) e `Serial2` (`GPIO 16/17` $\leftrightarrow$ Pinos 8/10 da RPi 3B).

### Instalação na Raspberry Pi 3B em 3 Comandos:
```bash
git clone -b develop https://github.com/joaopedro-prog/AGV.git
cd AGV
sudo bash scripts/rpi/setup_rpi.sh
sudo reboot
```

---

## 15. Configuração Inicial do Ambiente (PC / Notebook Novo)

### Pré-requisitos
1. Windows 10 (versão 21H2+) ou Windows 11 com virtualização ativada na BIOS.
2. **WSL 2** instalado com Ubuntu 24.04 (`wsl --install -d Ubuntu-24.04`).
3. **Docker Desktop** instalado com backend WSL 2 ativado.

### Clonando e Configurando
```powershell
git clone -b develop https://github.com/joaopedro-prog/AGV.git
cd AGV
```
Dê dois cliques em **[`scripts/atualizar_projeto.bat`](scripts/atualizar_projeto.bat)** e depois em **[`iniciar.bat`](iniciar.bat)**.

---

## 16. Solução de Problemas Comuns (Troubleshooting)

### Erro: `The command 'docker' could not be found in this WSL 2 distro`
* **Solução:** No Docker Desktop, abra **Settings** $\rightarrow$ **Resources** $\rightarrow$ **WSL integration**, ligue a chave do **Ubuntu-24.04** e clique em **Apply & restart**.

### Erro: `ERROR_NETNAME_DELETED` ou `E_UNEXPECTED` no WSL
* **Solução:** Feche o Docker Desktop, rode `wsl --shutdown` no PowerShell como Administrador e reabra o Docker Desktop.

---

## 👨‍💻 Autor e Licença

Desenvolvido para o projeto **ELETRON AGV Móvel Autônomo** com ROS 2 Humble.  
Licença: MIT.
