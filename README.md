# AGV Autonomous Mobile Robot - ROS 2 Humble

Ambiente completo de desenvolvimento, simulação e controle para **Robô Móvel Guiado (AGV / AMR)** utilizando **ROS 2 Humble**, **Gazebo Classic**, **RViz 2** e integração com **Docker + WSL 2 (Windows 10/11 com aceleração de GPU)** e transição direta para **Raspberry Pi 5 + Microcontrolador (Arduino/ESP32)**.

---

## 📑 Sumário

1. [Visão Geral e Arquitetura](#1-visão-geral-e-arquitetura)
2. [Estrutura de Pastas e Pacotes](#2-estrutura-de-pastas-e-pacotes)
3. [Como Executar no Dia a Dia (Scripts Rápidos)](#3-como-executar-no-dia-a-dia-scripts-rápidos)
4. [Simulação vs Robô Real](#4-simulação-vs-robô-real)
5. [Orquestração do Seguidor de Linha (START / STOP)](#5-orquestração-do-seguidor-de-linha-start--stop)
6. [Checklist Quando o Robô Físico Chegar](#6-checklist-quando-o-robô-físico-chegar)
7. [Configuração Inicial do Ambiente (PC / Notebook Novo)](#7-configuração-inicial-do-ambiente-pc--notebook-novo)
8. [Solução de Problemas Comuns (Troubleshooting)](#8-solução-de-problemas-comuns-troubleshooting)

---

## 1. Visão Geral e Arquitetura

O projeto foi projetado com uma separação clara entre **hardware físico**, **simulação gráfica** e **camada de inteligência**:

```text
                                [ CÂMERA USB / REAL ]                  [ MICROCONTROLADOR ] (ESP32/Arduino)
                                          │                                      ▲  (Motores, Encoders, Sensores)
                                          │ USB                                  │  USB Serial (/dev/ttyUSB0)
┌─────────────────────────────────────────┼──────────────────────────────────────┼──────────────────────────────┐
│ RASPBERRY PI (REAL) / DOCKER (SIMULAÇÃO)▼                                      ▼                              │
│                                 [v4l2_camera_node]                    [serial_bridge_node]                    │
│                                         │                                      ▲                              │
│                                         │ /camera/image_raw                    │ /cmd_vel                     │
│                                         ▼                                      │ (velocidade linear e angular)│
│                                [line_detector_node]                            │                              │
│                               (OpenCV: acha a fita)                            │                              │
│                                         │                                      │                              │
│                                         │ /agv/line_error                      │                              │
│                                         ▼                                      │                              │
│                             [line_follower_controller] ────────────────────────┘                              │
│                               (PID: calcula velocidade)                                                       │
│                                         ▲                                                                     │
│                                         │ /agv/command ("START", "STOP")                                      │
│                                    [SEU COMANDO] (Terminal / Scripts / Dashboard)                             │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Principais Características
* **Independência de Ambiente:** Os mesmos nós de visão e controle funcionam tanto no Gazebo quanto no robô físico real sem alterar o código-fonte.
* **Aceleração Gráfica por Hardware:** Suporte a D3D12/WSLg no WSL 2 para renderização fluida do Gazebo e RViz 2 no Windows.
* **Segurança e Watchdog:** Desaceleração automática em curvas, parada emergencial por detecção de obstáculo e timeout dos motores se a comunicação serial cair.

---

## 2. Estrutura de Pastas e Pacotes

```text
AGV/
├── .gitignore                    # Arquivos ignorados pelo Git (build, install, log, etc.)
├── dockerfile                    # Imagem ROS 2 Humble com todas as dependências instaladas
├── docker-compose.yml            # Orquestrador do container com montagem do workspace e GPU
├── iniciar.bat                   # [ATALHO PRINCIPAL] Menu interativo no Windows
├── README.md                     # Documentação completa do projeto
│
├── firmware/                     # Firmware do Microcontrolador
│   └── agv_mcu_firmware/
│       └── agv_mcu_firmware.ino  # Código C++ para Arduino / ESP32 / STM32
│
├── scripts/                      # Scripts de automação e atalhos Windows (.bat) e Linux (.sh)
│   ├── menu_agv.bat              # Menu interativo do AGV
│   ├── 1_ver_robo_rviz.bat       # Abre o RViz 2 com controles deslizantes das rodas
│   ├── 2_iniciar_simulacao.bat   # Abre o Gazebo com a pista e o robô
│   ├── 3_ver_camera.bat          # Monitor visual da detecção de linha (rqt_image_view)
│   ├── 4_agv_start.bat           # Manda o AGV começar a seguir linha (START)
│   ├── 5_agv_stop.bat            # Manda o AGV parar imediatamente (STOP)
│   ├── 6_painel_interativo.bat   # Painel CLI de missões do AGV
│   ├── compilar.bat              # Executa colcon build no workspace
│   ├── entrar_container.bat      # Abre um terminal bash direto dentro do container
│   ├── atualizar_projeto.bat     # Atualizador automático (git pull + docker + build)
│   └── ros_exec.sh               # Intermediador oficial Linux para carregar o ROS 2
│
├── src/                          # Código-fonte ROS 2 (3 Pacotes Principais)
│   ├── articubot_one/            # [PACOTE 1] Modelagem 3D, URDF/Xacro e Mundos Gazebo
│   │   ├── description/          # Arquivos Xacro (robot_core, camera, lidar, inertials)
│   │   ├── launch/               # Launches de simulação (launch_sim, view_robot, rsp)
│   │   └── worlds/               # Circuitos de simulação (circuit1.world com tiles)
│   │
│   ├── agv_hardware/             # [PACOTE 2] Ponte de Hardware Real e Orquestração
│   │   ├── agv_hardware/         # serial_bridge_node (USB Serial) e rpi_sensors_node (GPIO)
│   │   ├── config/               # hardware_params.yaml (portas USB, medidas físicas, encoders)
│   │   └── launch/               # agv_complete.launch.py (Orquestrador Mestre Sim vs Real)
│   │
│   └── agv_brain/                # [PACOTE 3] Inteligência, Visão Computacional e PID
│       ├── agv_brain/            # line_detector_node (OpenCV) e line_follower_node (PID)
│       ├── config/               # brain_params.yaml (ganhos PID, velocidades, cor da linha)
│       └── launch/               # brain.launch.py (detecção + seguidor de linha)
│
├── tiles/                        # Modelos 3D modulares de pista (tile-reta, curva, curva90)
└── gazebo_world/                 # Definições de circuitos industriais
```

---

## 3. Como Executar no Dia a Dia (Scripts Rápidos)

Na raiz do projeto no Windows, basta dar **dois cliques em `iniciar.bat`**.

O menu interativo será exibido:

```text
======================================================================
                    PAINEL DE CONTROLE DO AGV (ROS 2)
======================================================================

  [1] Abrir Terminal Interativo ROS 2 (bash dentro do container)
  [2] Visualizar Robo 3D no RViz 2 (com controles de rodas)
  [3] Iniciar SIMULACAO COMPLETA no Gazebo (Pista + Robo + Visao)
  [4] Ver Camera e Deteccao de Linha (rqt_image_view)

  -------------------------- COMANDOS DO AGV -------------------------
  [5] Mandar o Robo SEGUIR A LINHA (START)
  [6] Mandar o Robo PARAR IMEDIATAMENTE (STOP)
  [7] Abrir Painel Interativo de Missoes (agv_cmd)

  -------------------------- FERRAMENTAS -----------------------------
  [8] Recompilar o Workspace (colcon build)
  [9] Baixar Atualizacoes do GitHub (git pull + docker + build)
  [0] Sair
======================================================================
Digite o numero da opcao (0-9):
```

> **Dica:** Você também pode dar dois cliques diretamente nos arquivos dentro da pasta `scripts/` (ex: `scripts/2_iniciar_simulacao.bat`) para abrir tarefas específicas sem passar pelo menu.

---

## 4. Simulação vs Robô Real

O arquivo mestre [`src/agv_hardware/launch/agv_complete.launch.py`](src/agv_hardware/launch/agv_complete.launch.py) orquestra todo o sistema através do argumento `sim_mode`:

### A) Modo Simulação (No computador com Gazebo)
```bash
ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true
```
* Sobe o **Gazebo Classic** com a pista `circuit1.world`.
* Spawna o robô automaticamente sobre a faixa preta (`x=0.02, y=-0.07`).
* A câmera simulada renderiza frames virtuais e publica em `/camera/image_raw`.
* O nó de detecção e o controlador PID iniciam em modo de espera (`IDLE`).

### B) Modo Robô Real (Na Raspberry Pi 5)
```bash
ros2 launch agv_hardware agv_complete.launch.py sim_mode:=false
```
* O Gazebo **não é carregado** (economiza CPU e memória).
* Inicia o nó `serial_bridge` conectado à porta serial do microcontrolador (ex: `/dev/ttyUSB0`).
* Inicia o nó `v4l2_camera` lendo a webcam física via USB em `/camera/image_raw`.
* Inicia o leitor de botões físicos GPIO (`rpi_sensors_node`).
* O robô fica pronto para seguir a linha assim que receber o comando de início.

---

## 5. Orquestração do Seguidor de Linha (START / STOP)

Por segurança, o robô **sempre inicia parado** no estado `IDLE`. Ele só começa a seguir linha quando você autorizar.

Você pode enviar comandos de três formas:

1. **Pelo Menu Interativo / Atalhos:**
   * Opção `[5]` no menu (ou `scripts/4_agv_start.bat`) $\rightarrow$ Inicia o movimento.
   * Opção `[6]` no menu (ou `scripts/5_agv_stop.bat`) $\rightarrow$ Para imediatamente.

2. **Pelo Terminal CLI do ROS 2:**
   ```bash
   # Iniciar seguidor de linha
   ros2 run agv_brain agv_cmd start

   # Parar o robô
   ros2 run agv_brain agv_cmd stop

   # Painel interativo com menu
   ros2 run agv_brain agv_cmd
   ```

3. **Via Serviço ROS 2:**
   ```bash
   ros2 service call /agv/set_following std_srvs/srv/SetBool "{data: true}"
   ```

### Visualizar a Câmera e Detecção ao Vivo
Abra outro terminal (ou use a opção `[4]` do menu):
```bash
ros2 run rqt_image_view rqt_image_view /agv/line_debug_image
```
*Uma janela exibirá a visão do chão com a faixa delimitada em verde, o centro da imagem e o cálculo do desvio lateral em tempo real.*

---

## 6. Checklist Quando o Robô Físico Chegar

Quando o hardware físico chegar, você precisará editar **apenas 4 arquivos** onde estão as marcações `[ALTERAR]`:

### 1. Portas e Medidas em [`src/agv_hardware/config/hardware_params.yaml`](src/agv_hardware/config/hardware_params.yaml)
* `serial_port`: Porta onde o microcontrolador conectou na Raspberry (ex: `"/dev/ttyUSB0"` ou `"/dev/ttyACM0"`).
* `baud_rate`: Taxa de transmissão (padrão `115200`).
* `wheel_radius`: Raio da roda real em metros (ex: `0.033` = 3.3 cm).
* `wheel_separation`: Distância entre o centro das duas rodas em metros.
* `encoder_ticks_per_rev`: Quantidade de pulsos gerados pelo encoder para 1 volta completa da roda.
* `invert_left_motor` / `invert_right_motor`: Mude para `true` se alguma roda girar invertida.

### 2. Sintonia do PID em [`src/agv_brain/config/brain_params.yaml`](src/agv_brain/config/brain_params.yaml)
* `detection_mode`: `"dark_line"` (fita preta no chão claro) ou `"hsv"` (fita colorida).
* `base_linear_speed`: Velocidade para frente em reta ($m/s$).
* `kp`, `ki`, `kd`: Ganhos do controlador para deixar as curvas mais suaves ou agressivas.

### 3. Modelo 3D em [`src/articubot_one/description/robot_core.xacro`](src/articubot_one/description/robot_core.xacro)
* Ajuste as propriedades `chassis_length`, `chassis_width`, `chassis_height` e `wheel_radius` para refletir as dimensões reais do chassi.

### 4. Pinos do Microcontrolador em [`firmware/agv_mcu_firmware/agv_mcu_firmware.ino`](firmware/agv_mcu_firmware/agv_mcu_firmware.ino)
* Ajuste os pinos da Ponte H (`PIN_MOTOR_L_PWM`, `IN1`, `IN2`, etc.) e dos encoders de quadratura (`PIN_ENC_L_A`, `B`) para corresponder à ligação elétrica da sua placa e grave via Arduino IDE.

---

## 7. Configuração Inicial do Ambiente (PC / Notebook Novo)

Se você for clonar e rodar este projeto em um novo computador ou notebook:

### Pré-requisitos
1. Windows 10 (versão 21H2+) ou Windows 11 com virtualização ativada na BIOS.
2. **WSL 2** instalado com Ubuntu 24.04:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
3. **Docker Desktop** instalado no Windows com backend WSL 2 ativado.
4. No Docker Desktop, vá em:
   * **Settings (Engrenagem)** $\rightarrow$ **Resources** $\rightarrow$ **WSL integration**
   * Marque a opção do **`Ubuntu-24.04`** e clique em **Apply & restart**.

### Clonando e Configurando com 1 Clique
No Windows PowerShell:
```powershell
git clone https://github.com/joaopedro-prog/AGV.git
cd AGV
```
Dê dois cliques no arquivo **[`scripts/atualizar_projeto.bat`](scripts/atualizar_projeto.bat)**:
* Ele baixará atualizações pendentes do GitHub.
* Construirá a imagem Docker com todas as dependências automaticamente.
* Compilará o workspace ROS 2 (`colcon build`).
* Deixará o ambiente 100% pronto para você dar dois cliques no `iniciar.bat`!

---

## 8. Solução de Problemas Comuns (Troubleshooting)

### Erro: `The command 'docker' could not be found in this WSL 2 distro`
* **Causa:** A integração do Docker Desktop com o Ubuntu foi desativada ou o serviço do Docker reiniciou.
* **Solução:** No Docker Desktop, abra **Settings** $\rightarrow$ **Resources** $\rightarrow$ **WSL integration**, ligue a chavinha do **Ubuntu-24.04** e clique em **Apply & restart**.

### Erro: `ERROR_NETNAME_DELETED` ou `E_UNEXPECTED` no WSL
* **Causa:** A ponte de rede virtual do Hyper-V/WSL travou temporariamente no Windows.
* **Solução:**
  1. Feche o Docker Desktop completamente (botão direito no ícone perto do relógio $\rightarrow$ *Quit Docker Desktop*).
  2. No PowerShell como Administrador, execute:
     ```powershell
     wsl --shutdown
     ```
  3. Abra o Ubuntu (`wsl -d Ubuntu-24.04`) e depois reabra o Docker Desktop.

### Aceleração Gráfica no WSLg
Para verificar se a aceleração 3D via D3D12 está ativa no Linux:
```bash
glxinfo -B
```
O resultado deve indicar:
```text
OpenGL vendor string: Microsoft Corporation
OpenGL renderer string: D3D12 (...)
Accelerated: yes
```

---

## 👨‍💻 Autor e Licença

Desenvolvido para projeto de AGV Móvel com ROS 2 Humble.  
Licença: MIT.
