# 🚀 Guia Completo de Implantação no Robô Físico — ELETRON AGV (Raspberry Pi CM4 / 3B / 4B + ESP32)

> **Arquitetura Oficial:** Hardware KiCad Rev 2.0 + Container Docker ARM64 Headless (`Dockerfile.rpi`, zero simulação/Gazebo) + Roteador Dedicado `Eletron-AGV` + Deploy estilo FRC (`Ctrl+Shift+B` / `deploy_rpi.bat`).

---

## 1. Mapa Oficial de Ligações (KiCad Rev 2.0)

### 1.1 ESP32 DevKit V1 (`firmware/agv_mcu_firmware/agv_mcu_firmware.ino`)

| Pino ESP32 | Net KiCad | Dispositivo Conectado | Observação Técnica |
| :--- | :--- | :--- | :--- |
| **GPIO 13** | `PWM_LEFT` | `SPARK_L` (REV Spark MAX Esq.) | Sinal Servo PWM 50 Hz (`1000–2000 µs`, `1500 µs` neutro) |
| **GPIO 14** | `PWM_RIGHT` | `SPARK_R` (REV Spark MAX Dir.) | Sinal Servo PWM 50 Hz (`1000–2000 µs`, `1500 µs` neutro) |
| **GPIO 34 / 35** | `ENC1_CLK / DT` | Encoder `KY-040 #1` (Esquerdo) | Redução 20:1 $\rightarrow$ `800 ticks/volta` da roda (`CHANGE`) |
| **GPIO 39 (VN) / 36 (VP)** | `ENC2_CLK / DT` | Encoder `KY-040 #2` (Direito) | Redução 20:1 $\rightarrow$ `800 ticks/volta` da roda (`CHANGE`) |
| **GPIO 33** | `E_STOP_D33` | Botão Emergência `BTN_E_STOP` | `INPUT_PULLUP` ao GND |
| **GPIO 27** | `TRIG_SHARED` | Trigger `HC-SR04 #1` e `#2` | Pulso 10 µs não-bloqueante a 10 Hz |
| **GPIO 26 / 25** | `ECHO1_3V3 / ECHO2_3V3` | Eco Frontal Esquerdo (`US1`) e Direito (`US2`) | Obrigatório divisor resistivo **1k / 2k** ($5\text{V} \rightarrow 3{,}3\text{V}$) |
| **GPIO 16 / 17** | `RX2 / TX2` | RPi UART (`Pinos 8 e 10`) | Espelhada em paralelo com a USB Serial (`115200 bps`) |

### 1.2 Raspberry Pi CM4 (`CM4-to-Pi3-Adapter`) / 3B / 4B (`src/agv_hardware/`)

| Pino RPi (BCM) | Net KiCad | Periférico / ROS Node | Observação |
| :--- | :--- | :--- | :--- |
| **BCM 17 (Pino 11)** | `CTRL_FAN` | Relé `K1` (BC547) $\rightarrow$ Ventoinhas 12V | Acionado via `rpi_sensors` e botão ON/OFF no Dashboard Web |
| **BCM 27 (Pino 13)** | `CTRL_LED` | Relé `K2` (BC547) $\rightarrow$ Fita LED 5050 12V | Controle ON/OFF no Dashboard; pisca em E-Stop/alerta quando ligado |
| **BCM 2 / 3 (Pinos 3/5)** | `IMU_SDA / SCL` | MPU6050 I2C 3.3V (`0x68`) | Publica em `/imu/data_raw` (`rpi_sensors`) |
| **Porta `J_CSI` / USB** | `CSI_DATA/CLK` | Pi Camera CSI / USB V4L2 | Exposta em `/dev/video0` (`320×240 @ 15fps`) |
| **Pinos 8 / 10 (UART0)** | `TXD0 / RXD0` | ESP32 `GPIO 16 / 17` | Opcional se não usar cabo USB (`/dev/serial0`) |

---

## 2. Gravação do Firmware no ESP32

1. Abra [`firmware/agv_mcu_firmware/agv_mcu_firmware.ino`](../../firmware/agv_mcu_firmware/agv_mcu_firmware.ino) na **Arduino IDE** (ou PlatformIO).
2. Selecione **ESP32 Dev Module** (Core 2.x) e a porta COM correspondente.
3. Confira no topo do código `ESTOP_TRIGGER_LEVEL` (`LOW` para botão NA ao GND; `HIGH` para botão NF ao GND).
4. Faça o upload para o ESP32.
5. **Calibração inicial dos Spark MAX (rodas no ar!):** Com o ESP32 enviando `1500 µs` em repouso, verifique se o LED de status dos dois REV Spark MAX indica neutro calibrado.

---

## 3. Gravação do Sistema Operacional na Raspberry Pi

### Sistema Recomendado
- **Ubuntu Server 22.04 LTS (64-bit ARM64)** via **Raspberry Pi Imager** com personalização:
  - **Hostname:** `agv-raspberry`
  - **Usuário / Senha:** `agv` / `agv1234` (ou padrão da sua equipe)
  - **Localização:** `America/Sao_Paulo`, teclado `br`
  - **Serviços:** **Enable SSH** (*Use password authentication*)

### Caso Especial — Compute Module 4 (CM4) com eMMC + `CM4-to-Pi3-Adapter`
> [!IMPORTANT]
> **Módulos CM4 com memória eMMC interna ignoram fisicamente o slot de cartão microSD do `CM4-to-Pi3-Adapter`.** A imagem precisa ser gravada diretamente no eMMC via USB:

1. Instale o utilitário oficial `rpiboot` no Windows (`https://github.com/raspberrypi/usbboot/raw/master/win32/rpiboot_setup.exe`).
2. Retire qualquer cartão microSD, mude a chavinha **`BOOT`** do adaptador para **`ON`** e conecte um cabo USB de dados da porta USB traseira do PC até a micro-USB do adaptador.
3. No PowerShell do Windows, exponha o eMMC como disco:
   ```powershell
   & "C:\Program Files (x86)\Raspberry Pi\rpiboot.exe" -d "C:\Program Files (x86)\Raspberry Pi\msd"
   ```
4. No **Raspberry Pi Imager**, selecione **Dispositivo: `Raspberry Pi 4`**, **SO: `Ubuntu Server 22.04.5 LTS (64-bit)`**, e **Armazenamento: `RPi-MSD` (eMMC)**.
5. Após gravar, confira se `system-boot\config.txt` contém em `[cm4]`:
   ```ini
   [cm4]
   dtoverlay=dwc2,dr_mode=host
   ```
   *(Essa linha ativa as portas USB e Ethernet do `CM4-to-Pi3-Adapter`).*
6. Desconecte o cabo USB, **volte a chavinha `BOOT` para `OFF`** e energize a placa normalmente. Aguarde ~2 minutos no primeiro boot.

---

## 4. Provisionamento Inicial da Raspberry Pi (100% Offline — Sem Internet na RPi)

Como o roteador dedicado **`Eletron-AGV`** não precisa ter acesso à internet, toda a instalação (incluindo o próprio **Docker Engine ARM64**) é feita pelo seu PC Windows:

1. Conecte o seu PC à rede **`Eletron-AGV`** (mesmo roteador da Raspberry Pi).
2. Informe o IP inicial da Raspberry em [`scripts/rpi/rpi_target.env`](../../scripts/rpi/rpi_target.env) (ex.: `RPI_HOST=192.168.0.101`, `RPI_USER=agv`).
3. *(Recomendado — 1 única vez)* Instale a chave SSH do seu PC na Raspberry para deploys sem senha:
   ```powershell
   if (-not (Test-Path "$env:USERPROFILE\.ssh\id_ed25519")) { ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519" -N '""' }
   Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh agv@192.168.0.101 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   ```
4. Execute **[`instalar_rpi_offline.bat`](../../instalar_rpi_offline.bat)** (duplo clique no Windows):
   - Baixa os 5 `.deb` oficiais ARM64 do Docker Engine (`containerd.io`, `docker-ce`, `docker-ce-cli`, `docker-buildx-plugin`, `docker-compose-plugin`) no PC;
   - Compila `Dockerfile.rpi` para `linux/arm64` (zero Gazebo/RViz/mundos);
   - Envia código + `.deb` + imagem `.tar.gz` via SSH/SCP para a Raspberry;
   - Instala Docker offline (`dpkg -i`), configura I2C/UART/udev, carrega a imagem (`docker load`), apaga o `.tar.gz` para liberar eMMC e inicia o container **`agv_eletron_real`** com `restart: unless-stopped`.
   - *(Para uma segunda placa quando a imagem já estiver compilada no PC: `.\scripts\rpi\setup_offline_rpi.ps1 -SkipBuild`).*

### Alternativa Online (se a Raspberry Pi tiver acesso à internet)
```bash
git clone -b develop https://github.com/joaopedro-prog/AGV.git
cd AGV
sudo bash scripts/rpi/setup_rpi.sh
sudo reboot
```

---

## 5. Atualização de Código no Dia a Dia (Deploy Estilo FRC)

Após o provisionamento inicial, **nunca mais é preciso editar código por SSH nem recompilar a imagem Docker**:

1. Edite e teste normalmente no seu PC Windows (VS Code + Gazebo).
2. Conectado à rede **`Eletron-AGV`**, aperte **`Ctrl + Shift + B`** no VS Code (ou dê duplo clique em **[`deploy_rpi.bat`](../../deploy_rpi.bat)**).
3. O script [`scripts/rpi/agv_deploy.ps1`](../../scripts/rpi/agv_deploy.ps1):
   - Valida sintaxe Python/JS localmente (fail-fast);
   - Descobre a Raspberry automaticamente via Beacon UDP `:5800` (`agv_discover.ps1`);
   - Envia apenas os arquivos de produção (~`70 KB`) + `deploy_info.json`;
   - Reinicia em modo `FAST_SYMLINK` (~20s) ou recompila automaticamente no boot (`FULL_COLCON`) se houver arquivos novos ou alterações de estrutura;
   - Valida `http://<IP>:8080/api/status` online com a nova versão confirmada.

---

## 6. Checklist Obrigatório de Comissionamento em Bancada (Rodas no Ar!)

Antes de colocar o robô no piso pela primeira vez, execute esta sequência com o **chassi apoiado em cavalete**:

1. **Driver Station & AGVLog (`http://<IP_DA_RPI>:8080`):**
   - Confirme os LEDs **COMMS** (verde), **ROBOT CODE** (verde) e **ESP32 / HW** (verde com `ESP32 CONECTADO 30Hz` e `Erros CRC16: 0`).
   - Confira no badge superior o commit/horário do último deploy e abra a aba **📟 AGVLog** para verificar inicialização limpa de todos os nós.
2. **Teste de Emergência Física & Atalho `ESPAÇO` + Rearme em 5 Passos:**
   - Pressione `BTN_E_STOP` (`GPIO 33`) ou a tecla **`ESPAÇO`** no Dashboard: estado deve ir para `HARDWARE_ESTOP_ACTIVE`, LED K2 pisca e Spark MAX ficam travados em `1500 µs`.
   - Solte o botão $\rightarrow$ `RECOVERY_PENDING` $\rightarrow$ clique em **🔄 REARMAR SISTEMA (RESET)** $\rightarrow$ `IDLE`.
3. **Teste de Relés 12V (`K1` Ventoinha / `K2` LED):**
   - Alterne os botões de **Ventoinha (GPIO 17)** e **Fita LED 12V (GPIO 27)** no Cockpit e confirme o acionamento físico dos relés.
4. **Teste de Watchdog (`200 ms`):**
   - Com velocidade mínima no joystick, desconecte o cabo serial/USB ESP32 $\leftrightarrow$ RPi. Os motores devem parar em $\le 200\text{ ms}$ e `odometry_valid` ir para `false`.
5. **Conferência de Polaridade e Curva de Aceleração:**
   - Comande avanço no joystick: ambas as rodas devem girar para frente e `odom_x` aumentar positivamente. Se inverter, ajuste `invert_left_*` / `invert_right_*` em [`src/agv_hardware/config/hardware_params.yaml`](../../src/agv_hardware/config/hardware_params.yaml) e dê `Ctrl+Shift+B`.
   - Na aba **📈 Osciloscópio**, selecione o preset **📈 Curva de Aceleração** e valide que a velocidade real acompanha a curva `s_curve` do perfil escolhido (`SUAVE_CARGA` / `PADRAO` / `TURBO` / `PRECISAO`).
6. **Calibração no Piso:**
   - Meça `1,00 m` no chão e valide `/odom` $\approx 1.00\text{ m}$ (ajuste `wheel_radius` / `encoder_ticks_per_rev` se necessário).
   - Ajuste `dark_threshold` ou `hsv_lower/hsv_upper` em [`src/agv_brain/config/brain_params.yaml`](../../src/agv_brain/config/brain_params.yaml) conforme a iluminação real do piso.
