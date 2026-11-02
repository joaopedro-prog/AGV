# AGV Autonomous Mobile Robot - ROS 2 Humble

Ambiente completo de desenvolvimento, simulação e controle para **Robô Móvel Guiado (AGV / AMR)** utilizando **ROS 2 Humble**, **Gazebo Classic**, **RViz 2** e integração com **Docker + WSL 2 (Windows 10/11 com aceleração de GPU via Direct3D 12)** e transição direta para **Raspberry Pi 5 + Microcontrolador (Arduino/ESP32)**.

---

## 📑 Sumário

1. [Visão Geral e Arquitetura](#1-visão-geral-e-arquitetura)
2. [Estrutura de Pastas e Pacotes](#2-estrutura-de-pastas-e-pacotes)
3. [Como Executar no Dia a Dia (Menu Interativo)](#3-como-executar-no-dia-a-dia-menu-interativo)
4. [Mundos e Circuitos no Gazebo](#4-mundos-e-circuitos-no-gazebo)
5. [Aceleração por GPU e Otimização de Desempenho (60 FPS)](#5-aceleração-por-gpu-e-otimização-de-desempenho-60-fps)
6. [Posicionamento e Angulação da Câmera](#6-posicionamento-e-angulação-da-câmera)
7. [Simulação vs Robô Real](#7-simulação-vs-robô-real)
8. [Orquestração do Seguidor de Linha (START / STOP)](#8-orquestração-do-seguidor-de-linha-start--stop)
9. [Checklist Quando o Robô Físico Chegar](#9-checklist-quando-o-robô-físico-chegar)
10. [Configuração Inicial do Ambiente (PC / Notebook Novo)](#10-configuração-inicial-do-ambiente-pc--notebook-novo)
11. [Solução de Problemas Comuns (Troubleshooting)](#11-solução-de-problemas-comuns-troubleshooting)

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
* **Aceleração Gráfica por Hardware:** Suporte a D3D12/WSLg no WSL 2 para renderização fluida do Gazebo e RViz 2 no Windows (AMD Radeon e NVIDIA).
* **Segurança e Watchdog:** Desaceleração automática em curvas, parada emergencial e inicialização em modo de espera (`IDLE`).

---

## 2. Estrutura de Pastas e Pacotes

```text
AGV/
├── .gitignore                    # Arquivos ignorados pelo Git (build, install, log, etc.)
├── dockerfile                    # Imagem ROS 2 Humble com todas as dependências instaladas
├── docker-compose.yml            # Orquestrador do container com repasse de GPU D3D12 e volumes
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
│   ├── 2_iniciar_simulacao.bat   # Abre o Gazebo com seletor de mundos e robô
│   ├── 3_ver_camera.bat          # Monitor visual da detecção de linha (rqt_image_view)
│   ├── 4_agv_start.bat           # Manda o AGV começar a seguir linha (START)
│   ├── 5_agv_stop.bat            # Manda o AGV parar imediatamente (STOP)
│   ├── 6_painel_interativo.bat   # Painel CLI de missões do AGV
│   ├── verificar_gpu.bat         # Diagnóstico de GPU e teste visual de FPS (glxgears)
│   ├── compilar.bat              # Executa colcon build no workspace
│   ├── entrar_container.bat      # Abre um terminal bash direto dentro do container
│   ├── atualizar_projeto.bat     # Atualizador automático (git pull + docker + build)
│   └── ros_exec.sh               # Intermediador oficial Linux para carregar o ROS 2
│
├── src/                          # Código-fonte ROS 2 (3 Pacotes Principais)
│   ├── articubot_one/            # [PACOTE 1] Modelagem 3D, URDF/Xacro e Mundos Gazebo
│   │   ├── description/          # Arquivos Xacro (robot_core, camera, lidar, inertials)
│   │   ├── launch/               # Launches de simulação (launch_sim, view_robot, rsp)
│   │   └── worlds/               # Circuitos de simulação (3D Multinível, Oficial, 8 Tiles)
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
└── worlds/                       # Pasta raiz espelhada de circuitos do Gazebo
```

---

## 3. Como Executar no Dia a Dia (Menu Interativo)

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
  [G] Testar e Verificar Aceleracao da GPU (AMD / D3D12)
  [0] Sair
======================================================================
Digite a opcao:
```

---

## 4. Mundos e Circuitos no Gazebo

Ao escolher a opção **`[3]`** no menu, você pode selecionar qual circuito carregar:

| Mundo | Descrição | Destaques |
| :--- | :--- | :--- |
| **`pista_completa_3d.world`** | Pista 3D Multinível Completa | Rampas, viaduto elevado, pilares de sustentação e passagem subterrânea (túnel). |
| **`pista_oficial.world`** | Pista Oficial Completa | 38 tiles modulares com curvas retas e desafios de cruzamento. |
| **`pista_teste_8_tiles.world`** | Circuito Compacto de Teste | 8 tiles (90x90 cm), ideal para testes rápidos e validação de algoritmo PID. |
| **`pista_obstaculos.world`** | Pista com Obstáculos | Elementos estáticos na pista para teste de parada e desvio. |
| **`mundo_vazio.world`** | Mundo Vazio | Chão plano padrão para teleoperação e testes livres. |

---

## 5. Aceleração por GPU e Otimização de Desempenho (60 FPS)

O ambiente utiliza repasse direto de hardware via WSLg (`/dev/dxg` e `GALLIUM_DRIVER=d3d12`), comunicando-se nativamente com sua GPU (**AMD Radeon RX 580** ou **NVIDIA Geforce**).

### Como Verificar a Aceleração
1. Abra o menu `iniciar.bat` e escolha **`G`** (ou dê duplo clique em `scripts/verificar_gpu.bat`).
2. O script identifica a placa de vídeo no Windows e exibe os dados do Linux:
   ```text
   Device: D3D12 (AMD Radeon RX 580 2048SP)
   Accelerated: yes
   Video memory: 16290MB
   ```
3. Você também pode rodar o teste visual das engrenagens 3D (`glxgears`).

### Por que manter sombras dinâmicas desligadas em circuitos complexos?
* **Física ODE (CPU):** Roda a `Real Time Factor: 1.00` cravados.
* **Renderização 3D (GPU):** Ao ativar sombras dinâmicas em mundos com 40 modelos 3D elevados, o motor OGRE 1.9 do Gazebo trava o loop esperando mapas de sombra a cada quadro (*pipeline stall*). Com sombras leves/desativadas, a interface atinge **60 FPS** fluidos.

---

## 6. Posicionamento e Angulação da Câmera

A câmera do AGV é parametrizada no arquivo [`src/articubot_one/description/camera.xacro`](src/articubot_one/description/camera.xacro):

```xml
<joint name="camera_joint" type="fixed">
    <parent link="chassis"/>
    <child link="camera_link"/>
    <origin xyz="0.210 0 0.090" rpy="0 0.80 0"/>
</joint>
```

### Tabela de Inclinação (Pitch em Radianos):
* `rpy="0 0.00 0"` $\rightarrow$ **0°** (Horizontal, olha para o horizonte).
* `rpy="0 0.35 0"` $\rightarrow$ **20°** (Olha para o horizonte e piso distante).
* `rpy="0 0.52 0"` $\rightarrow$ **30°** (Visão mista: foca piso de 15 cm a 60 cm).
* `rpy="0 0.80 0"` $\rightarrow$ **46°** (**Padrão Atual**: foca chão próximo de 10 cm a 35 cm, ideal para curvas fechadas e rampas).
* `rpy="0 1.57 0"` $\rightarrow$ **90°** (Totalmente vertical, olhando direto para o chão).

---

## 7. Simulação vs Robô Real

O arquivo mestre [`src/agv_hardware/launch/agv_complete.launch.py`](src/agv_hardware/launch/agv_complete.launch.py) orquestra todo o sistema através do argumento `sim_mode`:

### A) Modo Simulação (No computador com Gazebo)
```bash
ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true world:=pista_completa_3d.world
```
* Sobe o Gazebo Classic com o circuito selecionado.
* Spawna o robô automaticamente sobre a faixa preta.
* A câmera virtual renderiza os frames em `/camera/image_raw`.
* O robô inicia no estado seguro `IDLE` (parado).

### B) Modo Robô Real (Na Raspberry Pi 5)
```bash
ros2 launch agv_hardware agv_complete.launch.py sim_mode:=false
```
* O Gazebo **não é carregado** (economiza 100% dos recursos da Raspberry Pi).
* Inicia o nó `serial_bridge` conectado à porta serial do microcontrolador (ex: `/dev/ttyUSB0`).
* Inicia o nó `v4l2_camera` lendo a webcam física via USB em `/camera/image_raw`.
* Inicia o leitor de botões físicos GPIO (`rpi_sensors_node`).

---

## 8. Orquestração do Seguidor de Linha (START / STOP)

Por segurança, o robô **sempre inicia parado** no estado `IDLE`. Ele só começa a seguir linha quando você autorizar.

Você pode enviar comandos de três formas:

1. **Pelo Menu Interativo / Atalhos:**
   * Opção `[5]` no menu (ou `scripts/4_agv_start.bat`) $\rightarrow$ Inicia o movimento (**START**).
   * Opção `[6]` no menu (ou `scripts/5_agv_stop.bat`) $\rightarrow$ Para imediatamente (**STOP**).

2. **Pelo Terminal CLI do ROS 2:**
   ```bash
   ros2 run agv_brain agv_cmd start
   ros2 run agv_brain agv_cmd stop
   ros2 run agv_brain agv_cmd
   ```

3. **Monitor Visual da Câmera:**
   Opção `[4]` no menu (ou `scripts/3_ver_camera.bat`):
   ```bash
   ros2 run rqt_image_view rqt_image_view /agv/line_debug_image
   ```

---

## 9. Checklist Quando o Robô Físico Chegar

Quando o hardware físico chegar, você precisará editar **apenas 4 arquivos** onde estão as marcações `[ALTERAR]`:

### 1. Portas e Medidas em [`src/agv_hardware/config/hardware_params.yaml`](src/agv_hardware/config/hardware_params.yaml)
* `serial_port`: Porta onde o microcontrolador conectou na Raspberry (ex: `"/dev/ttyUSB0"` ou `"/dev/ttyACM0"`).
* `baud_rate`: Taxa de transmissão (padrão `115200`).
* `wheel_radius`: Raio da roda real em metros (ex: `0.025` = 2.5 cm).
* `wheel_separation`: Distância entre o centro das duas rodas em metros (`0.160` = 16 cm).
* `encoder_ticks_per_rev`: Quantidade de pulsos gerados pelo encoder para 1 volta completa da roda.
* `invert_left_motor` / `invert_right_motor`: Mude para `true` se alguma roda girar invertida.

### 2. Sintonia do PID em [`src/agv_brain/config/brain_params.yaml`](src/agv_brain/config/brain_params.yaml)
* `detection_mode`: `"dark_line"` (fita preta no chão claro) ou `"hsv"` (fita colorida).
* `base_linear_speed`: Velocidade para frente em reta ($m/s$).
* `kp`, `ki`, `kd`: Ganhos do controlador para deixar as curvas mais suaves ou agressivas.

### 3. Modelo 3D em [`src/articubot_one/description/robot_core.xacro`](src/articubot_one/description/robot_core.xacro)
* Dimensões compactadas de 20 cm ajustadas para tiles padrão de 30 cm.

### 4. Pinos do Microcontrolador em [`firmware/agv_mcu_firmware/agv_mcu_firmware.ino`](firmware/agv_mcu_firmware/agv_mcu_firmware.ino)
* Ajuste os pinos da Ponte H (`PIN_MOTOR_L_PWM`, `IN1`, `IN2`, etc.) e dos encoders de quadratura (`PIN_ENC_L_A`, `B`).

---

## 10. Configuração Inicial do Ambiente (PC / Notebook Novo)

### Pré-requisitos
1. Windows 10 (versão 21H2+) ou Windows 11 com virtualização ativada na BIOS.
2. **WSL 2** instalado com Ubuntu 24.04:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
3. **Docker Desktop** instalado com backend WSL 2 ativado.
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
* Deixará o ambiente pronto para você executar `iniciar.bat`.

---

## 11. Solução de Problemas Comuns (Troubleshooting)

### Erro: `The command 'docker' could not be found in this WSL 2 distro`
* **Solução:** No Docker Desktop, abra **Settings** $\rightarrow$ **Resources** $\rightarrow$ **WSL integration**, ligue a chavinha do **Ubuntu-24.04** e clique em **Apply & restart**.

### Erro: `ERROR_NETNAME_DELETED` ou `E_UNEXPECTED` no WSL
* **Solução:**
  1. Feche o Docker Desktop completamente (*Quit Docker Desktop*).
  2. No PowerShell como Administrador:
     ```powershell
     wsl --shutdown
     ```
  3. Reabra o Docker Desktop.

### Testar Aceleração Gráfica
Dentro do container:
```bash
glxinfo -B
```
Deverá exibir:
```text
OpenGL vendor string: Microsoft Corporation
OpenGL renderer string: D3D12 (...)
Accelerated: yes
```

---

## 👨‍💻 Autor e Licença

Desenvolvido para projeto de AGV Móvel com ROS 2 Humble.  
Licença: MIT.
