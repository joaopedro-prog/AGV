# AGV Autonomous Mobile Robot - ROS 2 Humble

Ambiente completo de desenvolvimento, simulação física de alta fidelidade e controle autônomo para **Robô Móvel Guiado (AGV / AMR)** utilizando **ROS 2 Humble**, **Gazebo Classic**, **RViz 2** e integração com **Docker + WSL 2 (Windows 10/11 com aceleração de GPU via Direct3D 12)** e transição direta para **Raspberry Pi 5 + Microcontrolador (Arduino/ESP32)**.

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
9. [Posicionamento e Sensores (Câmera e Ultrassônico)](#9-posicionamento-e-sensores-câmera-e-ultrassônico)
10. [Simulação vs Robô Real](#10-simulação-vs-robô-real)
11. [Orquestração do Seguidor de Linha (START / STOP)](#11-orquestração-do-seguidor-de-linha-start--stop)
12. [Teleoperação por Joystick USB (Simulação e Robô Real)](#12-teleoperação-por-joystick-usb-simulação-e-robô-real)
13. [Checklist Quando o Robô Físico Chegar](#13-checklist-quando-o-robô-físico-chegar)
14. [Configuração Inicial do Ambiente (PC / Notebook Novo)](#13-configuração-inicial-do-ambiente-pc--notebook-novo)
15. [Solução de Problemas Comuns (Troubleshooting)](#14-solução-de-problemas-comuns-troubleshooting)

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
* **Modelo CAD Real Integrado:** Malhas 3D exportadas diretamente do Fusion 360 com propriedades físicas calculadas por densidade real (Alumínio e Poliuretano).
* **Tração Diferencial Confiável:** Rodas motrizes com contato esférico de precisão; 4 rodízios passivos (rodas bobas) com folga calibrada anti-tombamento para garantir tração máxima sem perda de contato normal.
* **Aceleração Gráfica por Hardware:** Suporte a D3D12/WSLg no WSL 2 para renderização fluida do Gazebo e RViz 2 no Windows (AMD Radeon e NVIDIA).
* **Segurança e Watchdog:** Desaceleração automática em curvas, parada emergencial e inicialização em modo de espera (`IDLE`).

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
> **Dinâmica de Rodagem:** Apenas a roda esquerda e a roda direita são tracionadas pelo plugin diferencial (`libgazebo_ros_diff_drive.so`). Os 4 rodízios nos cantos são **rodas bobas passivas** com atrito nulo ($\mu = 0.001$) e folga vertical de segurança de $3\text{ mm}$, garantindo que $100\%$ do peso do AGV repouse sobre as rodas tracionadas, assegurando aderência máxima tanto em piso plano quanto nas rampas 3D.

---

## 3. Estrutura de Pastas e Pacotes

```text
AGV/
├── .gitignore                    # Arquivos ignorados pelo Git (build, install, log, temporários)
├── dockerfile                    # Imagem ROS 2 Humble com todas as dependências instaladas
├── docker-compose.yml            # Orquestrador do container com repasse de GPU D3D12 e volumes
├── iniciar.bat                   # [ATALHO PRINCIPAL] Menu interativo no Windows
├── README.md                     # Documentação completa do projeto
│
├── docs/                         # Contratos Formais de Interface e Arquitetura
│   └── contracts/
│       ├── protocolo_serial_esp32_rpi.md          # Framing, CRC16-CCITT, Watchdog 200ms
│       ├── catalogo_topicos_e_servicos_ros2.md    # Tópicos, QoS e Prioridades do twist_mux
│       └── maquina_estados_seguranca.md           # 3 Níveis de Parada e Procedimento de Rearme
│
├── firmware/                     # Firmware do Microcontrolador
│   └── agv_mcu_firmware/
│       └── agv_mcu_firmware.ino  # Firmware C++ ESP32 com CRC16, Watchdog e PID de Velocidade
│
├── scripts/                      # Scripts de automação e atalhos Windows (.bat) e Linux (.sh)
│   ├── menu_agv.bat              # Menu interativo do AGV
│   ├── 1_ver_robo_rviz.bat       # Abre o RViz 2 com robô real, odometria, rodas e pista
│   ├── 2_iniciar_simulacao.bat   # Abre o Gazebo com seletor de mundos e robô
│   ├── 3_ver_camera.bat          # Monitor visual da detecção de linha (rqt_image_view)
│   ├── 4_agv_start.bat           # Manda o AGV começar a seguir linha (START)
│   ├── 5_agv_stop.bat            # Manda o AGV parar imediatamente (STOP)
│   ├── 6_painel_interativo.bat   # Painel CLI de missões do AGV
│   ├── 7_menu_gazebo.bat         # Menu de comandos rápidos do Gazebo em janela dedicada
│   ├── 8_abrir_dashboard.bat     # Abre o Cockpit Web HMI em http://localhost:8080
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
│   │   ├── description/          # Arquivos Xacro (robot_core, camera, ultrasonic, etc.)
│   │   ├── meshes/               # 16 malhas STL reais do robô exportadas do Fusion 360
│   │   ├── launch/               # Launches de simulação (launch_sim, view_robot, rsp)
│   │   └── worlds/               # Circuitos de simulação (3D Multinível, Oficial, 8 Tiles)
│   │
│   ├── agv_hardware/             # [PACOTE 2] Ponte de Hardware Real e Orquestração
│   │   ├── agv_hardware/         # serial_bridge_node (USB Serial) e rpi_sensors_node (GPIO)
│   │   ├── config/               # hardware_params.yaml (portas USB, medidas físicas, encoders)
│   │   └── launch/               # agv_complete.launch.py (Orquestrador Mestre Sim vs Real)
│   │
│   ├── agv_brain/                # [PACOTE 3] Inteligência, Visão Computacional e PID
│       ├── agv_brain/            # line_detector_node (OpenCV) e line_follower_node (PID)
│       ├── config/               # brain_params.yaml (ganhos PID, velocidades, cor da linha)
│       └── launch/               # brain.launch.py (detecção + seguidor de linha)
│   │
│   └── agv_dashboard/            # [PACOTE 4] Dashboard Web, HMI e Telemetria em Tempo Real
│       ├── agv_dashboard/        # dashboard_node.py (Servidor HTTP + Bridge de Telemetria)
│       ├── static/               # index.html (Cockpit Industrial Responsivo)
│       └── launch/               # dashboard.launch.py (Launch do Servidor Web na porta 8080)
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
* Executa `git add -A`, grava o `git commit` e envia via `git push origin main`.

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

Os circuitos do Gazebo foram redimensionados para a escala **$4.0\times$** (tiles de $1.20\text{ m} \times 1.20\text{ m}$, raio de curvatura de $0.60\text{ m}$), mantendo a proporção ideal para a bitola de $0.468\text{ m}$ e comprimento de $0.70\text{ m}$ do robô real. Além disso, o chão e horizonte de todos os mundos foram padronizados em **Branco Puro** (`Gazebo/White`), proporcionando contraste máximo e sem ruído para o sensor de visão da câmera sobre as linhas pretas:

| Mundo | Descrição | Destaques |
| :--- | :--- | :--- |
| **`armazem_logistico.world`** | ★ **Armazém Fabril / Estoque com Gôndolas** | Galpão industrial com paredes, docas de carga, 4 blocos de gôndolas porta-paletes (com pallets de madeira, caixas e containers), circuito cíclico de linha contínua e **5 marcações coloridas de estações** para fusão com odometria. |
| **`pista_completa_plana.world`** | Pista Plana Completa com Bypass | 32 tiles escalados ($1.20\text{ m}$), curvas amplas ($R=0.60\text{ m}$), retas de alta velocidade e rotatória central. |
| **`pista_oficial.world`** | Pista Oficial Modular | Circuito com retas de $1.20\text{ m}$, curvas amplas de $90^\circ$ ($R=0.60\text{ m}$) e pista de alta velocidade. |
| **`pista_teste_8_tiles.world`** | Circuito Compacto de Teste | 8 tiles ($3.6\times 3.6\text{ m}$, $R=0.60\text{ m}$), ideal para validação ágil do algoritmo PID e testes de visão. |
| **`pista_obstaculos.world`** | Pista com Obstáculos | Elementos estáticos na pista (cones e barris espaçados) para teste de parada e desvio autônomo. |
| **`mundo_vazio.world`** | Mundo Vazio | Chão plano branco padrão para teleoperação e testes livres. |

---



### Estações e Marcadores de Cores no `armazem_logistico.world`
O circuito possui 5 marcações transversais de alta visibilidade posicionadas diretamente sobre a linha preta:

| Estação / Setor | Cor Gazebo | Código RGB | Coordenadas $(X, Y)$ | Ação e Significado no Processo |
| :--- | :--- | :--- | :--- | :--- |
| **Estação 1: Doca de Entrada** | `Gazebo/Green` | `#00E676` (Verde) | $(X = -2.40, Y = 3.00)$ | Ponto de partida (Spawn) e recebimento/abastecimento de carga |
| **Estação 2: Picking Estoque A** | `Gazebo/Blue` | `#2979FF` (Azul) | $(X = 4.20, Y = 1.20)$ | Coleta de itens e insumos no bloco de gôndolas A |
| **Estação 3: Interseção Central** | `Gazebo/Turquoise` | `#00E5FF` (Ciano) | $(X = 0.00, Y = 0.00)$ | Verificação de tráfego, decisão de rota e bypass |
| **Estação 4: Picking Estoque B** | `Gazebo/Yellow` | `#FFEA00` (Amarelo) | $(X = 0.00, Y = -3.00)$ | Coleta de itens e insumos no bloco de gôndolas B |
| **Estação 5: Doca de Expedição** | `Gazebo/Red` | `#FF1744` (Vermelho) | $(X = -4.20, Y = -0.60)$ | Descarga final de material expedido |

> [!TIP]
> **Fusão de Visão com Odometria:** A câmera inferior detecta a cor do chão no centro do quadro visual (`/camera/image_raw`), e o nó de localização valida simultaneamente se a odometria está no raio da coordenada esperada, garantindo 100% de precisão de parada sem depender de marcadores externos ou de iluminação variável.

---

## 8. Aceleração por GPU e Otimização de Desempenho (60 FPS)

O ambiente utiliza repasse direto de hardware via WSLg (`/dev/dxg` e `GALLIUM_DRIVER=d3d12`), comunicando-se nativamente com sua GPU (**AMD Radeon RX 580** ou **NVIDIA GeForce**).

### Como Verificar a Aceleração
1. Abra o menu `iniciar.bat` e escolha **`G`** (ou dê duplo clique em `scripts/verificar_gpu.bat`).
2. O script identifica a placa de vídeo no Windows e exibe os dados do Linux:
   ```text
   Device: D3D12 (AMD Radeon RX 580 2048SP)
   Accelerated: yes
   Video memory: 16290MB
   ```
3. Você também pode rodar o teste visual das engrenagens 3D (`glxgears`).

---

## 9. Posicionamento e Sensores (Câmera e Ultrassônico)

O robô conta com sensores integrados focados em navegação por linha e segurança:

### 1. Câmera Inferior de Rastreamento (Webcam)
* **Arquivo:** [`src/articubot_one/description/camera.xacro`](src/articubot_one/description/camera.xacro)
* **Posição:** Integrada à abertura inferior do chassi ($x = 0.2557\text{ m}, z = -0.0163\text{ m}$).
* **Inclinação:** $0.60\text{ rad}$ ($\approx 34^\circ$ para baixo), focando o piso de $15\text{ cm}$ a $60\text{ cm}$ à frente do robô.
* **Tópico:** `/camera/image_raw` e HUD de depuração em `/agv/line_debug_image`.

### 2. Sensor Laser 360° (LiDAR)
* **Arquivo:** [`src/articubot_one/description/lidar.xacro`](src/articubot_one/description/lidar.xacro)
* **Posição:** Montado no topo do AGV ($z = 0.1604\text{ m}$) com visualização 360° desobstruída.
* **Tópico:** `/scan` (`sensor_msgs/msg/LaserScan`).

### 2. Sensor de Distância Dianteiro (Ultrassônico)
* **Arquivo:** [`src/articubot_one/description/ultrasonic.xacro`](src/articubot_one/description/ultrasonic.xacro)
* **Posição:** Para-choque frontal dianteiro ($x = 0.355\text{ m}, z = 0.050\text{ m}$).
* **Tópico:** `/agv/ultrasonic` (`sensor_msgs/msg/Range`, cone de $30^\circ$, alcance $2\text{ cm}$ a $3.0\text{ m}$).

---

## 10. Simulação vs Robô Real

O arquivo mestre [`src/agv_hardware/launch/agv_complete.launch.py`](src/agv_hardware/launch/agv_complete.launch.py) orquestra todo o sistema através do argumento `sim_mode`:

### A) Modo Simulação (No computador com Gazebo)
```bash
ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true world:=pista_completa_plana.world
```
* Sobe o Gazebo Classic com o circuito selecionado.
* Spawna o robô CAD com física de tração nas duas rodas e casters passivos.
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

## 11. Orquestração do Seguidor de Linha (START / STOP)

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

---

## 12. Teleoperação por Joystick USB (Simulação e Robô Real)

O sistema conta com suporte completo para controle manual por **Joystick / Gamepad USB** (Xbox 360/One/Series, PlayStation DualShock/DualSense ou controles genéricos USB).

### Destaques e Funcionamento:
* **Detecção Automática ou Seleção de Porta:** Ao iniciar, o sistema escaneia todos os joysticks e portas USB/COM disponíveis. Se houver apenas 1 controle conectado, basta pressionar ENTER para detecção automática, ou escolher o índice desejado.
* **Sem Janela Atrapalhando a Visão:** O script oferece a opção de **minimizar a janela automaticamente**, permitindo que você acompanhe a visão em tela cheia do Gazebo, RViz 2 ou da câmera sem nenhuma janela de terminal na frente.
* **Resposta em Segundo Plano (SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS):** Mesmo com o terminal minimizado ou atrás das janelas gráficas, o controle responde instantaneamente aos comandos dos botões e analógicos.
* **Controle Duplo (Simulado ou Real):**
  * **Simulação Local (Gazebo / Docker):** Transmissão com latência sub-milissegundo via pipe direto para o nó 	eleop_joy_receiver.py dentro do container.
  * **Robô Físico Real:** Envio de pacotes via socket UDP (porta 9876) diretamente para o IP da Raspberry Pi 5 pela rede local Wi-Fi.
* **Prioridade Absoluta via 	wist_mux:** Os comandos manuais do joystick são publicados em /cmd_vel_joy com **prioridade máxima (100)**, assumindo o controle instantâneo do robô mesmo se ele estiver no modo autônomo de seguidor de linha.

### Mapeamento dos Controles:
| Comando / Botão | Ação no AGV |
| :--- | :--- |
| **Alavanca Esquerda (Vertical)** | Movimento para frente / marcha a ré suave com curva exponencial |
| **Alavanca Esquerda / Direita (Horizontal)** | Rotação / curva (esterçamento para esquerda ou direita) |
| **D-Pad (Setas direcionais)** | Ajuste fino e alinhamento milimétrico passo a passo |
| **Gatilho Direito (RT / RB)** | **Modo TURBO:** Eleva a velocidade linear máxima para .85\text{ m/s}$ e angular para .80\text{ rad/s}$ |
| **Gatilho Esquerdo (LT / LB)** | **Modo LENTO / PRECISÃO:** Reduz a velocidade para .15\text{ m/s}$ para manobras delicadas |
| **Botão B (Círculo)** | **PARADA DE EMERGÊNCIA:** Trava os motores imediatamente e bloqueia novos comandos |
| **Botão A (Cruz)** | **Liberar Emergência:** Desbloqueia o robô e retoma a teleoperação normal |
| **Botão Back / Select** | Encerra o script com parada suave de segurança do robô |

### Como Usar:
1. Conecte o controle USB no computador.
2. No menu principal iniciar.bat, digite **[J]** (ou dê duplo clique em controlar_joystick.bat).
3. Confirme a detecção automática com ENTER e aproveite a pilotagem!

---

## 13. Dashboard Web Cockpit (Telemetria, HMI e os 3 Níveis de Parada)

O AGV conta com um painel de controle industrial responsivo em navegador web (HTML5 / WebSocket / REST), acessível em:
**`http://localhost:8080`** (ou via IP da máquina na rede local Wi-Fi).

### Como Iniciar:
* No menu `iniciar.bat`, escolha **`[W]`** (ou dê duplo clique em `scripts/8_abrir_dashboard.bat`).

### Destaques e Funcionalidades:
* **Banner de Status Unificado (3 Níveis de Parada):**
  * 🟡 **`REMOTE_STOP_REQUESTED` (Amarelo pulsante):** Parada remota solicitada pelo operador; robô aplicando rampa suave de desaceleração.
  * 🔵 **`STOP_CONFIRMED` (Azul estável):** Encoders com velocidade zero comprovada e confirmação eletrônica do ESP32; robô imobilizado em standby.
  * 🔴 **`HARDWARE_ESTOP_ACTIVE` (Vermelho piscante com alarme):** Emergência física acionada (botão cogumelo mecânico ou watchdog de 200 ms). **Corte físico imediato de potência dos motores**. Bloqueio total até realização do procedimento formal de rearme em 5 passos.
* **Telemetria ao Vivo:** Tensão da bateria (V), velocidade linear e angular real, odometria acumulada (X, Y), indicador dinâmico de desvio da linha e integridade de link serial (erros CRC16).
* **Controles Operacionais e D-Pad Virtual:** Botões START, STOP, PARADA DE EMERGÊNCIA (prioridade 255 no `twist_mux`), REARMAR SISTEMA e D-pad tátil para pilotagem remota.

---

## 14. Checklist Quando o Robô Físico Chegar

Quando o hardware físico chegar, você precisará editar **apenas 4 arquivos** onde estão as marcações `[ALTERAR]`:

### 1. Portas e Medidas em [`src/agv_hardware/config/hardware_params.yaml`](src/agv_hardware/config/hardware_params.yaml)
* `serial_port`: Porta onde o microcontrolador conectou na Raspberry (ex: `"/dev/ttyUSB0"` ou `"/dev/ttyACM0"`).
* `baud_rate`: Taxa de transmissão (padrão `115200`).
* `wheel_radius`: Raio da roda real em metros (`0.0762` = 7.62 cm / 6 polegadas).
* `wheel_separation`: Distância entre o centro das duas rodas motrizes em metros (`0.468` = 46.8 cm).
* `encoder_ticks_per_rev`: Quantidade de pulsos gerados pelo encoder para 1 volta completa da roda.
* `invert_left_motor` / `invert_right_motor`: Mude para `true` se alguma roda girar invertida.

### 2. Sintonia do PID em [`src/agv_brain/config/brain_params.yaml`](src/agv_brain/config/brain_params.yaml)
* `detection_mode`: `"dark_line"` (fita preta no chão claro) ou `"hsv"` (fita colorida).
* `base_linear_speed`: Velocidade para frente em reta ($m/s$).
* `kp`, `ki`, `kd`: Ganhos do controlador para deixar as curvas mais suaves ou agressivas.

### 3. Modelo 3D em [`src/articubot_one/description/robot_core.xacro`](src/articubot_one/description/robot_core.xacro)
* Já está com as malhas CAD reais e os parâmetros físicos sincronizados.

### 4. Pinos do Microcontrolador em [`firmware/agv_mcu_firmware/agv_mcu_firmware.ino`](firmware/agv_mcu_firmware/agv_mcu_firmware.ino)
* Ajuste os pinos da Ponte H (`PIN_MOTOR_L_PWM`, `IN1`, `IN2`, etc.) e dos encoders de quadratura (`PIN_ENC_L_A`, `B`).

---

## 15. Configuração Inicial do Ambiente (PC / Notebook Novo)

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

## 16. Solução de Problemas Comuns (Troubleshooting)

### Erro: `The command 'docker' could not be found in this WSL 2 distro`
* **Solução:** No Docker Desktop, abra **Settings** $\rightarrow$ **Resources** $\rightarrow$ **WSL integration**, ligue a chave do **Ubuntu-24.04** e clique em **Apply & restart**.

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

Desenvolvido para projeto de AGV Móvel Autônomo com ROS 2 Humble.  
Licença: MIT.
