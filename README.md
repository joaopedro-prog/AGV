# ELETRON AGV — Autonomous Mobile Robot (ROS 2 Humble)

Plataforma completa de desenvolvimento, simulação física de alta fidelidade e operação embarcada para o **Robô Móvel Autônomo (ELETRON AGV)** baseada em **ROS 2 Humble**, **Raspberry Pi CM4 / 3B / 4B (ARM64 Headless sem simulação)**, **ESP32 DevKit V1**, **2× REV Spark MAX** e **2× Motores CIM 2.5"**.

O fluxo de conexão, deploy e diagnóstico foi inspirado no ecossistema da **FIRST Robotics Competition (FRC — roboRIO / GradleRIO / WPILib VS Code / Driver Station)**:
- **Rede dedicada do robô (`Eletron-AGV`)** com **descoberta automática via Beacon UDP (`:5800`)** — sem precisar descobrir IP manualmente.
- **Deploy 100% offline em 1 clique** direto do **VS Code (`Ctrl + Shift + B`)** ou por **`deploy_rpi.bat`**, com pré-validação local de sintaxe, modo rápido `FAST_SYMLINK` e zero arquivos de simulação enviados à Raspberry Pi.
- **Dashboard Web estilo FRC Driver Station (`http://<IP>:8080`)** com 3 LEDs de status (**COMMS**, **ROBOT CODE**, **ESP32 / HW**), badge do último deploy ativo, atalho **`ESPAÇO` = E-STOP**, controle dos relés 12V, curvas de aceleração (Curva S / Trapezoidal), osciloscópio multi-node e console **AGVLog** ao vivo (`/rosout`).

---

## 📑 Sumário

1. [Visão Geral e Arquitetura](#1-visão-geral-e-arquitetura)
2. [Estrutura Limpa do Repositório](#2-estrutura-limpa-do-repositório)
3. [Hardware Real (KiCad Rev 2.0) e Modelo CAD](#3-hardware-real-kicad-rev-20-e-modelo-cad)
4. [Deploy Estilo FRC no Dia a Dia (VS Code `Ctrl+Shift+B` / `deploy_rpi.bat`)](#4-deploy-estilo-frc-no-dia-a-dia-vs-code-ctrlshiftb--deploy_rpibat)
5. [Dashboard Web HMI, Driver Station, Osciloscópio & AGVLog](#5-dashboard-web-hmi-driver-station-osciloscópio--agvlog)
6. [Curvas de Aceleração e Perfis de Movimento](#6-curvas-de-aceleração-e-perfis-de-movimento)
7. [Como Implantar em uma Nova Raspberry Pi (CM4 / 3B / 4B — Online ou 100% Offline)](#7-como-implantar-em-uma-nova-raspberry-pi-cm4--3b--4b--online-ou-100-offline)
8. [Simulação no PC Windows (Gazebo Classic + RViz 2 + GPU D3D12)](#8-simulação-no-pc-windows-gazebo-classic--rviz-2--gpu-d3d12)
9. [Teleoperação por Joystick USB e Comandos de Missão](#9-teleoperação-por-joystick-usb-e-comandos-de-missão)
10. [Configuração Inicial em um Novo PC Windows](#10-configuração-inicial-em-um-novo-pc-windows)
11. [Solução de Problemas Comuns (Troubleshooting)](#11-solução-de-problemas-comuns-troubleshooting)

---

## 1. Visão Geral e Arquitetura

O projeto separa estritamente a **camada de simulação (apenas no PC)** do **runtime embarcado de produção (apenas na Raspberry Pi, sem Gazebo/RViz/X11)**:

```text
                       [ CÂMERA CSI / USB V4L2 ]              [ ESP32 DevKit V1 ]
                                   │                                  ▲  (2x Spark MAX PWM 50Hz, 2x KY-040 20:1,
                                   │ /dev/video0                      │   2x HC-SR04 Frontais, E-Stop GPIO 33)
┌──────────────────────────────────┼──────────────────────────────────┼──────────────────────────────────────────┐
│ RASPBERRY PI (CM4/3B/4B) DOCKER  ▼                                  ▼  UART 115200 bps (CRC16-CCITT, 30 Hz)   │
│                          [v4l2_camera_node]                [serial_bridge_node]        [rpi_sensors_node]      │
│                                  │                                  ▲  │ /agv/ultrasonic_*    │ /imu/data_raw  │
│                                  │ /camera/image_raw                │  │ /odom                │ Relés K1 / K2  │
│                                  ▼                                  │  ▼                      ▼                │
│                         [line_detector_node]                        │ [agv_dashboard_node :8080]               │
│                        (OpenCV ROI: acha a fita)                    │ (Driver Station + MJPEG + Scope + /rosout│
│                                  │                                  │  AGVLog + Relés + Perfis de Movimento)   │
│                                  │ /agv/line_error                  │                                          │
│                                  ▼                                  │ /diff_cont/cmd_vel_unstamped             │
│                  [line_follower_node (PID + S-Curve)] ──► [twist_mux] ┘                                        │
│                                                           ▲                                                    │
│                                                           │ /cmd_vel_joy (Prio 100) / /cmd_vel_emergency (255) │
│                     [agv_beacon.py :5800 UDP]   [teleop_joy_receiver :9876 UDP]                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Prioridades de Segurança (`twist_mux`)
A hierarquia definida em [`src/agv_description/config/twist_mux.yaml`](src/agv_description/config/twist_mux.yaml) é imutável:
1. **`/cmd_vel_emergency` (Prioridade `255`):** E-Stop físico (`GPIO 33`), Watchdog `200 ms`, tecla `ESPAÇO` no Dashboard.
2. **`/cmd_vel_joy` (Prioridade `100`):** Joystick USB / Teleoperação manual.
3. **`/cmd_vel_line` (Prioridade `30`):** Controlador PID seguidor de linha com curva de aceleração.
4. **`/cmd_vel_tracker` (`20`) / `/cmd_vel` (`10`):** Comandos auxiliares/standby.

---

## 2. Estrutura Limpa do Repositório

```text
AGV/
├── .vscode/
│   └── tasks.json                # Tasks estilo WPILib (Ctrl+Shift+B Deploy, AGVLog, Discovery)
├── dockerfile                    # Imagem Desktop Completa (PC / Gazebo / RViz 2 / WSLg D3D12)
├── docker-compose.yml            # Orquestrador de Simulação no PC Windows
├── Dockerfile.rpi                # Imagem ARM64 Headless de Produção (SEM Gazebo, SEM RViz, SEM mundos)
├── docker-compose.rpi.yml        # Orquestrador Embarcado na Raspberry Pi (restart: unless-stopped)
├── iniciar.bat                   # Menu interativo principal no Windows (Simulação / Ferramentas)
├── deploy_rpi.bat                # [1 CLIQUE] Deploy rápido de código para a Raspberry Pi (sem internet)
├── instalar_rpi_offline.bat      # [1ª VEZ] Provisionamento 100% offline de uma nova Raspberry Pi
├── controlar_joystick.bat        # Teleoperação por Joystick USB (Simulado ou Wi-Fi UDP :9876)
├── AGENTS.md                     # Governança técnica e contratos de arquitetura
├── README.md                     # Documentação principal
│
├── docs/
│   ├── contracts/                # Contratos formais de protocolo serial CRC16, tópicos ROS 2 e FSM NR-12
│   └── hardware/
│       ├── guia_implantacao_robo_fisico.md   # Guia passo a passo completo (CM4 eMMC, RPi, ESP32, bancada)
│       ├── circuito_potencia.md              # Memorial descritivo elétrico 12V (KiCad Rev 2.0)
│       ├── circuito_potencia_agv.drawio      # Esquemático editável Draw.io
│       └── circuito_potencia_agv.svg         # Esquemático vetorial
│
├── firmware/
│   └── agv_mcu_firmware/
│       └── agv_mcu_firmware.ino  # Firmware ESP32 (2x Spark MAX 50Hz, 2x KY-040 20:1, 2x HC-SR04, CRC16)
│
├── scripts/
│   ├── rpi/
│   │   ├── agv_beacon.py                 # Beacon UDP :5800 (Auto-Discovery estilo FRC roboRIO)
│   │   ├── agv_discover.ps1              # Descobre automaticamente IP/versão da RPi na rede Eletron-AGV
│   │   ├── agv_deploy.ps1                # Motor de deploy estilo GradleRIO (validação + FAST_SYMLINK)
│   │   ├── agv_logs.ps1                  # Console AGVLog (estilo RioLog) no terminal do VS Code
│   │   ├── setup_offline_rpi.ps1         # Empacota Docker .deb + imagem ARM64 e instala 100% offline
│   │   ├── rpi_remote_setup_offline.sh   # Instalador executado na RPi offline (Docker .deb, I2C, UART, udev)
│   │   ├── setup_rpi.sh                  # Instalador alternativo para RPi com acesso à internet
│   │   ├── entrypoint_rpi.sh             # Entrypoint de produção (auto-build seguro, Beacon, Teleop, ROS 2)
│   │   ├── 99-agv-devices.rules          # Regras udev (/dev/agv_esp32, /dev/agv_cam, GPIO, I2C)
│   │   └── rpi_target.env                # Último IP/usuário descoberto automaticamente
│   ├── menu_agv.bat / 1_..8_*.bat        # Atalhos do ambiente de simulação no Windows
│   ├── tcp_proxy.py                      # Ponte TCP localhost:8080 -> container Windows
│   ├── teleop_joy_receiver.py            # Receptor ROS 2 de Joystick (Pipe local ou UDP :9876)
│   ├── controlar_joystick.py             # Cliente Windows de Joystick USB
│   ├── gazebo_cmd.py                     # Hot-reload, teleporte e luz no Gazebo
│   └── ros_exec.sh                       # Loader de ambiente ROS 2 Humble + GPU D3D12
│
├── src/                          # 4 Pacotes ROS 2 Oficiais do Projeto
│   ├── agv_description/          # [PACOTE 1] URDF/Xacro, malhas CAD 3D, twist_mux, RViz e mundos Gazebo
│   │   ├── config/               # twist_mux.yaml, gazebo_params.yaml, sim_robot.rviz, view_bot.rviz
│   │   ├── description/          # robot.urdf.xacro, robot_core, camera, ultrasonic (2x HC-SR04)
│   │   ├── launch/               # rsp.launch.py, launch_sim.launch.py, view_robot.launch.py
│   │   ├── meshes/               # 16 malhas STL exportadas do Fusion 360 (excluídas na imagem RPi)
│   │   └── worlds/               # armazem_logistico.world, pista_completa_plana.world, pista_teste_8_tiles.world
│   │
│   ├── agv_hardware/             # [PACOTE 2] HAL Raspberry Pi & ESP32 + Orquestração Mestre
│   │   ├── agv_hardware/         # serial_bridge_node.py (CRC16 30Hz) e rpi_sensors_node.py (Relés K1/K2 + MPU6050)
│   │   ├── config/               # hardware_params.yaml (portas, KY-040 800 ticks/rev, pinos BCM 17/27)
│   │   └── launch/               # agv_complete.launch.py e hardware_bringup.launch.py
│   │
│   ├── agv_brain/                # [PACOTE 3] Visão Computacional OpenCV + PID + Curvas de Aceleração
│   │   ├── agv_brain/            # line_detector_node.py, line_follower_node.py (S-Curve/Trap/Perfis), agv_commander_node.py
│   │   ├── config/               # brain_params.yaml (PID, perfis de movimento, Jerk, detecção de linha)
│   │   └── launch/               # brain.launch.py
│   │
│   └── agv_dashboard/            # [PACOTE 4] Dashboard Web HMI + Driver Station + Osciloscópio + AGVLog
│       ├── agv_dashboard/        # dashboard_node.py (REST, MJPEG, Histórico 10Hz, /rosout AGVLog)
│       ├── static/               # index.html (Cockpit, Osciloscópio Multi-Node e Console AGVLog)
│       └── launch/               # dashboard.launch.py
│
└── tiles/                        # Modelos 3D modulares de pista usados pelos mundos Gazebo
```

---

## 3. Hardware Real (KiCad Rev 2.0) e Modelo CAD

### Eletrônica Oficial (Sem LiDAR — 2× Ultrassônicos Frontais)
- **Computador Embarcado:** Raspberry Pi **CM4 (eMMC + Wi-Fi + `CM4-to-Pi3-Adapter`)**, 3B ou 4B rodando Ubuntu Server 22.04 LTS (64-bit ARM64).
- **Roteador Dedicado:** Rede local dedicada **`Eletron-AGV`** conectada à Raspberry Pi (equivalente ao rádio da FRC).
- **Microcontrolador:** ESP32 DevKit V1 (`firmware/agv_mcu_firmware/agv_mcu_firmware.ino`) em UART `115200 bps` com **CRC16-CCITT** e **Watchdog 200 ms**:
  - **Motores (2× REV Spark MAX + CIM 2.5"):** Servo PWM 50 Hz (`1000–2000 µs`, `1500 µs` neutro) em `GPIO 13` (`PWM_LEFT`) e `GPIO 14` (`PWM_RIGHT`).
  - **Encoders (2× KY-040 em redução 20:1 = `800 ticks/volta`):** `GPIO 34/35` (Esq.) e `GPIO 39/36` (Dir.).
  - **2× Ultrassônicos Frontais (`HC-SR04` com divisor `1k/2k`):** `TRIG_SHARED = GPIO 27`, `ECHO1 = GPIO 26` (Esq.), `ECHO2 = GPIO 25` (Dir.) $\rightarrow$ `/agv/ultrasonic_left` e `/agv/ultrasonic_right`.
  - **Botão Emergência Físico (`BTN_E_STOP`):** `GPIO 33` (`INPUT_PULLUP`).
- **GPIO e Sensores da Raspberry Pi (`rpi_sensors_node.py`):**
  - **Relé K1 (`BCM GPIO 17` / Pino 11):** Ventoinhas 12V (controle manual ON/OFF pelo Dashboard).
  - **Relé K2 (`BCM GPIO 27` / Pino 13):** Fita LED 5050 12V (controle manual ON/OFF pelo Dashboard + alerta piscante quando ligada em emergência).
  - **IMU 6-DOF (`MPU6050`):** I2C `BCM 2/3` (`/dev/i2c-1`, `0x68`) $\rightarrow$ `/imu/data_raw`.
  - **Câmera Inferior:** CSI / USB V4L2 (`/dev/video0`, `320×240 @ 15 FPS`) $\rightarrow$ `/camera/image_raw`.

### Modelo CAD Real (`src/agv_description`)
- Massa estrutural total calibrada: **$\approx 9.75\text{ kg}$** (chassi Alumínio 6061-T6 $\approx 9.19\text{ kg}$, 2 rodas motrizes PU $\varnothing = 0.1524\text{ m}$, bitola $0.468\text{ m}$, 4 rodízios passivos anti-tombamento com folga de $3\text{ mm}$).

---

## 4. Deploy Estilo FRC no Dia a Dia (VS Code `Ctrl+Shift+B` / `deploy_rpi.bat`)

Você edita e testa todo o código normalmente no **VS Code do seu PC Windows**, sem precisar editar nada via SSH:

### Como fazer deploy na Raspberry Pi (sem internet)
1. Conecte o seu PC à rede do roteador **`Eletron-AGV`**.
2. No **VS Code**, aperte **`Ctrl + Shift + B`** (ou dê duplo clique em **[`deploy_rpi.bat`](deploy_rpi.bat)**).
3. O motor [`scripts/rpi/agv_deploy.ps1`](scripts/rpi/agv_deploy.ps1) executa automaticamente:
   - **Fase 1 (Fail-Fast):** valida sintaxe de todos os `.py` (`py_compile`) e do JavaScript do Dashboard (`node --check`). Se houver erro, aborta **antes** de tocar no robô.
   - **Fase 2 (Auto-Discovery):** dispara broadcast UDP na porta `5800` (`agv_discover.ps1`) e encontra o IP da Raspberry automaticamente (com fallback para mDNS / cache).
   - **Fase 3 (Empacotamento Enxuto + Manifesto):** gera `deploy_info.json` (commit, branch, data/hora, PC) e empacota apenas o código de produção (~`70 KB`, zero arquivos de simulação).
   - **Fase 4 (Deploy Inteligente):**
     - **`FAST_SYMLINK` (~20s total com boot completo):** quando só arquivos `.py`, `.yaml`, `.html` ou `.sh` existentes foram editados, aplica via volume montado sem recompilar `colcon`.
     - **`FULL_COLCON`:** quando há arquivos novos ou alteração em `setup.py` / `package.xml` / `CMakeLists.txt` / `launch/`, marca `.needs_colcon_build` e o próprio `entrypoint_rpi.sh` recompila todos os 4 pacotes antes de lançar os nós ROS 2 (sem condição de corrida).

### Tasks prontas no VS Code (`.vscode/tasks.json`)
Abra **Terminal $\rightarrow$ Run Task** para acessar:
- **`AGV: Deploy Robot Code (Rapido)`** *(atalho padrão **`Ctrl + Shift + B`**)*
- **`AGV: Deploy Robot Code + AGVLog (estilo RioLog)`** *(faz deploy e já abre os logs ao vivo no terminal)*
- **`AGV: Deploy Completo (Force Colcon Build)`**
- **`AGV: AGVLog (Logs ao Vivo da Raspberry)`**
- **`AGV: Descobrir Robo & Abrir Driver Station (Dashboard)`**

---

## 5. Dashboard Web HMI, Driver Station, Osciloscópio & AGVLog

Acessível em **`http://<IP_DA_RPI>:8080`** no robô físico (ou **`http://localhost:8080`** na simulação via opção `[W]` do menu):

### Barra Superior Estilo FRC Driver Station
- **3 LEDs de prontidão:** **COMMS** (link HTTP com a Raspberry), **ROBOT CODE** (`line_follower` + `twist_mux` ativos), **ESP32 / HW** (serial 30 Hz + CRC16).
- **Badge de Deploy Ativo:** exibe hostname da Raspberry, hash do commit, horário exato do último deploy, modo (`FAST_SYMLINK` / `FULL_COLCON`) e uptime.
- **Atalho Global de Segurança:** apertar **`ESPAÇO`** no teclado (fora de campos de texto) dispara **E-STOP (Prioridade 255)** instantaneamente.

### 3 Abas Integradas
1. **🕹️ Cockpit & Operação:**
   - Botões **START**, **STOP**, **E-STOP**, **RESET** e D-pad de teleoperação manual.
   - **Relés 12V da Raspberry Pi:** botões liga/desliga ao vivo para **Ventoinha (Relé K1 • GPIO 17)** e **Fita LED 12V (Relé K2 • GPIO 27)**.
   - **Perfis & Curva de Aceleração:** seleção em tempo real de perfil, tipo de curva, sliders ajustáveis e pré-visualização gráfica da resposta.
   - **Câmera MJPEG ao vivo (`/api/camera_stream`)** com troca entre HUD de detecção de linha e câmera crua.
   - **Radar dos 2× Ultrassônicos Frontais** (`US1 Esq` / `US2 Dir`), **IMU MPU6050 6-DOF**, odometria, bateria e contador CRC16.
2. **📈 Osciloscópio & Telemetria por Node:**
   - **1 Escopo Unificado** ou **2 Escopos (A + B)** em `<canvas>` HiDPI, janelas de `15s / 30s / 60s / 120s`, cursor interativo (*crosshair* com tooltip), tabela de estatísticas (Atual / Mín / Máx / Média) e **Exportar CSV**.
   - Catálogo de sinais agrupados por node ROS 2 (`/twist_mux & Motores`, `/line_follower`, `/line_detector`, `/serial_bridge & /odom`, `/rpi_sensors`, `/agv_dashboard_node`) com **Presets de 1 clique** (incluindo *Motor: Vel. Comandada vs Real*, *Curva de Aceleração*, *Rodas Esq/Dir rad/s*, *Malha PID*, *Ultrassônicos*, *IMU* e *Energia & Relés*).
3. **📟 AGVLog (Console ao Vivo):**
   - Leitor nativo do tópico **`/rosout`** (`GET /api/logs`) com cores por severidade (`DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`), filtro por nó/nível/texto, pausa de auto-scroll, download `.log` e detecção automática de reinício pós-deploy.

---

## 6. Curvas de Aceleração e Perfis de Movimento

Implementados em [`src/agv_brain/agv_brain/line_follower_node.py`](src/agv_brain/agv_brain/line_follower_node.py) e configuráveis em [`src/agv_brain/config/brain_params.yaml`](src/agv_brain/config/brain_params.yaml) ou ao vivo pelo Dashboard (`/agv/motion_profile_command` e `/agv/motion_profile_status`):

| Perfil | Vel. Base | Vel. Mín. Curva | Acel. Máx. | Frenagem Máx. | Jerk Máx. | Curva Padrão | Indicação |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`SUAVE_CARGA`** | `0.20 m/s` | `0.10 m/s` | `0.25 m/s²` | `0.45 m/s²` | `0.80 m/s³` | `s_curve` | Carga frágil / partida ultra suave |
| **`PADRAO`** | `0.35 m/s` | `0.15 m/s` | `0.50 m/s²` | `0.80 m/s²` | `2.00 m/s³` | `s_curve` | Operação logística nominal |
| **`TURBO`** | `0.55 m/s` | `0.22 m/s` | `1.00 m/s²` | `1.40 m/s²` | `5.00 m/s³` | `trapezoidal` | Deslocamento rápido |
| **`PRECISAO`** | `0.14 m/s` | `0.08 m/s` | `0.18 m/s²` | `0.40 m/s²` | `0.60 m/s³` | `s_curve` | Aproximação de doca / manobra fina |

- **Modos de curva selecionáveis:** **`s_curve`** (limitação de Jerk $da/dt$ sem *overshoot*), **`trapezoidal`** (rampa linear) e **`direto`** (degrau instantâneo).
- **Segurança:** paradas de emergência físicas/ultrassônicas cortam a velocidade instantaneamente sem esperar a rampa.

---

## 7. Como Implantar em uma Nova Raspberry Pi (CM4 / 3B / 4B — Online ou 100% Offline)

O guia detalhado completo (incluindo gravação do **eMMC no CM4 com `rpiboot`**, `CM4-to-Pi3-Adapter`, pinagem KiCad Rev 2.0 e checklist de bancada) está em:
👉 **[`docs/hardware/guia_implantacao_robo_fisico.md`](docs/hardware/guia_implantacao_robo_fisico.md)**

### Resumo Rápido — Troca ou Instalação em Nova Raspberry Pi (100% Offline)
1. Grave **Ubuntu Server 22.04 LTS (64-bit ARM64)** na nova placa com usuário `agv`, SSH habilitado e rede configurada:
   - **Se for CM4 com eMMC + `CM4-to-Pi3-Adapter`:** ative a chave `BOOT = ON`, conecte via USB no PC, rode `& "C:\Program Files (x86)\Raspberry Pi\rpiboot.exe" -d "C:\Program Files (x86)\Raspberry Pi\msd"`, grave no Raspberry Pi Imager (**Dispositivo: Raspberry Pi 4**), confira `dtoverlay=dwc2,dr_mode=host` em `system-boot\config.txt`, e volte **`BOOT = OFF`**.
   - **Se for RPi 3B / 4B / CM4 Lite:** grave direto no cartão microSD pelo Raspberry Pi Imager.
2. Conecte a nova Raspberry no roteador **`Eletron-AGV`** e coloque o IP dela em [`scripts/rpi/rpi_target.env`](scripts/rpi/rpi_target.env).
3. *(Opcional — SSH sem senha para deploy em 1 clique)* Copie a chave SSH do seu PC uma única vez:
   ```powershell
   Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh agv@<IP_NOVA_RPI> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   ```
4. Dê um duplo clique em **[`instalar_rpi_offline.bat`](instalar_rpi_offline.bat)**:
   - Baixa os 5 `.deb` oficiais do Docker Engine ARM64 no PC (com internet), compila `Dockerfile.rpi` para `linux/arm64` (sem simulação), envia tudo por SSH, instala o Docker offline, carrega a imagem e sobe `agv_eletron_real` no boot.
   - *(Dica: se a imagem já estiver pronta no seu PC, rode `.\scripts\rpi\setup_offline_rpi.ps1 -SkipBuild` para instalar em ~2 minutos!)*
5. A partir daí, use apenas **`Ctrl + Shift + B`** no VS Code ou **[`deploy_rpi.bat`](deploy_rpi.bat)**.

*(Caso a nova Raspberry tenha acesso à internet, você também pode optar pelo modo online tradicional: `git clone -b develop https://github.com/joaopedro-prog/AGV.git && cd AGV && sudo bash scripts/rpi/setup_rpi.sh && sudo reboot`).*

---

## 8. Simulação no PC Windows (Gazebo Classic + RViz 2 + GPU D3D12)

Dê dois cliques em **[`iniciar.bat`](iniciar.bat)** na raiz do projeto para abrir o painel interativo de simulação:
- **`[2]` RViz 2:** visualiza o modelo CAD real (`agv_description`), odometria e sensores.
- **`[3]` Simulação Completa no Gazebo:** escolhe entre os 3 circuitos em `src/agv_description/worlds/`:
  - **`armazem_logistico.world`** *(galpão fabril com gôndolas, docas e 5 estações coloridas)*
  - **`pista_completa_plana.world`** *(circuito completo escala 4× com rotatória e bypass)*
  - **`pista_teste_8_tiles.world`** *(circuito compacto 3,6 m × 3,6 m para ajuste rápido de PID)*
- **`[W]` Dashboard Web Local:** abre `http://localhost:8080` conectado ao Gazebo via ponte TCP automática (`scripts/tcp_proxy.py`).
- **`[Z]` Comandos Rápidos do Gazebo:** Hot-Reload do URDF, teleporte para largada/rampa, pausa e iluminação.
- **`[G]` Verificar GPU:** valida aceleração WSLg Direct3D 12 (`GALLIUM_DRIVER=d3d12`).

---

## 9. Teleoperação por Joystick USB e Comandos de Missão

- **Joystick USB (Xbox / PlayStation / genérico):** dê duplo clique em **[`controlar_joystick.bat`](controlar_joystick.bat)** (envia via pipe no Gazebo ou via UDP porta `9876` para o IP da Raspberry Pi, prioridade `100` no `twist_mux`).
- **Comandos autônomos:** pelo Dashboard Web (**START / STOP / E-STOP / RESET**), pelo menu `[5]`/`[6]` ou via CLI (`ros2 run agv_brain agv_cmd start|stop`).

---

## 10. Configuração Inicial em um Novo PC Windows

1. Instale **WSL 2 (Ubuntu 24.04)**, **Docker Desktop** (com integração WSL 2 ativa), **Git** e **VS Code**.
2. Clone o repositório na branch `develop`:
   ```powershell
   git clone -b develop https://github.com/joaopedro-prog/AGV.git
   cd AGV
   ```
3. Para simulação no PC: execute [`scripts/atualizar_projeto.bat`](scripts/atualizar_projeto.bat) e depois [`iniciar.bat`](iniciar.bat).
4. Para deploy no robô físico: conecte no Wi-Fi `Eletron-AGV` e aperte **`Ctrl + Shift + B`** no VS Code (ou rode [`deploy_rpi.bat`](deploy_rpi.bat)).

---

## 11. Solução de Problemas Comuns (Troubleshooting)

- **`agv_discover.ps1` não encontra o robô:** verifique se o PC está conectado ao roteador `Eletron-AGV` e se o container `agv_eletron_real` está ativo (`ssh agv@<IP> docker ps`).
- **CM4 com eMMC ignora o cartão SD no `CM4-to-Pi3-Adapter`:** comportamento normal de hardware do CM4 com eMMC — grave sempre direto no eMMC via `rpiboot` com chave `BOOT = ON`, depois volte `BOOT = OFF`.
- **USB / Ethernet não funciona no `CM4-to-Pi3-Adapter`:** confirme `dtoverlay=dwc2,dr_mode=host` na seção `[cm4]` de `/boot/firmware/config.txt`.
- **Docker não encontrado no WSL 2 (Windows):** no Docker Desktop, habilite *Settings $\rightarrow$ Resources $\rightarrow$ WSL integration $\rightarrow$ Ubuntu-24.04*.
- **Gazebo lento / sem aceleração no Windows:** rode `iniciar.bat` $\rightarrow$ `[G]` para confirmar `Device: D3D12` e atualize o WSL (`wsl --update`).
