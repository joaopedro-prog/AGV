# 🚀 Guia de Implantação no Robô Físico — ELETRON AGV (Raspberry Pi 3B + ESP32)

> **Arquitetura:** Hardware real baseado no Esquemático KiCad Rev 2.0 + Container Docker ARM64 Headless (`Dockerfile.rpi`, zero simulação/Gazebo).

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
| **GPIO 26 / 25** | `ECHO1_3V3 / ECHO2_3V3` | Eco Frontal e Traseiro | Obrigatório divisor resistivo **1k / 2k** ($5\text{V} \rightarrow 3{,}3\text{V}$) |
| **GPIO 16 / 17** | `RX2 / TX2` | RPi UART (`Pinos 8 e 10`) | Espelhada em paralelo com a USB Serial (`115200 bps`) |

### 1.2 Raspberry Pi 3 Model B (`src/agv_hardware/`)

| Pino RPi (BCM) | Net KiCad | Periférico / Ros Node | Observação |
| :--- | :--- | :--- | :--- |
| **BCM 17 (Pino 11)** | `CTRL_FAN` | Relé `K1` (BC547) $\rightarrow$ Fans #1 e #2 | Acionado via `rpi_sensors` (`auto_fan_enable: true`) |
| **BCM 27 (Pino 13)** | `CTRL_LED` | Relé `K2` (BC547) $\rightarrow$ Fita LED 5050 | Contínuo em operação normal; pisca em E-Stop/alerta |
| **BCM 2 / 3 (Pinos 3/5)** | `IMU_SDA / SCL` | MPU6050 I2C 3.3V (`0x68`) | Publica em `/imu/data_raw` (`rpi_sensors`) |
| **Porta `J_CSI`** | `CSI_DATA/CLK` | Pi Camera CSI (`CAM1`) | Exposta em `/dev/video0` via `bcm2835-v4l2` (`320×240 @ 15fps`) |
| **Pinos 8 / 10 (UART0)** | `TXD0 / RXD0` | ESP32 `GPIO 16 / 17` | Opcional se não usar cabo USB (`/dev/serial0`) |

---

## 2. Gravação do Firmware no ESP32

1. Abra [`firmware/agv_mcu_firmware/agv_mcu_firmware.ino`](file:///c:/Users/João%20Pedro/Documents/AGV/firmware/agv_mcu_firmware/agv_mcu_firmware.ino) na **Arduino IDE** (ou PlatformIO).
2. Selecione a placa **ESP32 Dev Module** (Core 2.x) e porta COM correspondente.
3. Confira no topo do código:
   - `ESTOP_TRIGGER_LEVEL`: `LOW` para contato NA ligado ao GND (padrão KiCad `SW_Push`) ou altere para `HIGH` caso utilize botão físico NF ligado ao GND.
4. Faça o upload para o ESP32.
5. **Calibração inicial dos Spark MAX:** Conecte apenas a bateria com as **rodas suspensas no cavalete**. Com o ESP32 enviando `1500 µs` em repouso, verifique se o LED de status dos dois REV Spark MAX pisca azul/ciano (neutro calibrado).

---

## 3. Preparação da Raspberry Pi 3B (Sem Simulação)

1. Instale no cartão microSD o **Ubuntu Server 22.04 LTS (64-bit ARM64)** ou **Raspberry Pi OS Lite (64-bit)** (sem interface desktop).
2. Clone o repositório na Raspberry Pi e mude para a branch atual:
   ```bash
   git clone https://github.com/joaopedro-prog/AGV.git
   cd AGV
   ```
3. Se conectar ESP32 e RPLIDAR A1 via USB simultaneamente:
   - Rode `udevadm info -a -n /dev/ttyUSB0 | grep serial` em cada dispositivo e ajuste [`scripts/rpi/99-agv-devices.rules`](file:///c:/Users/João%20Pedro/Documents/AGV/scripts/rpi/99-agv-devices.rules).
   - Se conectar o ESP32 pelos pinos GPIO 8/10 (`Serial2`), defina `serial_port: "/dev/serial0"` em [`src/agv_hardware/config/hardware_params.yaml`](file:///c:/Users/João%20Pedro/Documents/AGV/src/agv_hardware/config/hardware_params.yaml).
4. Execute o script automático de provisionamento:
   ```bash
   sudo bash scripts/rpi/setup_rpi.sh
   sudo reboot
   ```
5. Após reiniciar, o container **`agv_eletron_real`** inicia automaticamente no boot (`restart: unless-stopped`):
   - **Dashboard Web HMI:** `http://<IP_DA_RPI>:8080`
   - **Teleoperação Joystick Wi-Fi:** no notebook Windows, rode `controlar_joystick.bat` apontando para o IP da RPi na porta UDP `9876`.
   - **Para habilitar o RPLIDAR A1:** defina `ENABLE_LIDAR=true` no ambiente ou edite `docker-compose.rpi.yml`.

---

## 4. Checklist Obrigatório de Comissionamento em Bancada (Rodas no Ar!)

Antes de colocar o robô no piso pela primeira vez, execute esta sequência com o **chassi apoiado em cavalete** (rodas livres):

1. **Verificação Serial & CRC16:**
   - Acesse `http://<IP_DA_RPI>:8080` e confirme `Serial: CONECTADO (30Hz)` e `Erros CRC: 0`.
2. **Teste de Emergência Física & Rearme em 5 Passos:**
   - Pressione `BTN_E_STOP` (`GPIO 33`): o estado deve ir imediatamente para `HARDWARE_ESTOP_ACTIVE`, os LEDs K2 devem piscar e os Spark MAX devem permanecer travados em `1500 µs`.
   - Solte o botão $\rightarrow$ estado muda para `RECOVERY_PENDING`.
   - Clique em **"REARMAR"** no Dashboard $\rightarrow$ retorna para `IDLE`.
3. **Teste de Watchdog (200 ms):**
   - Com uma velocidade mínima comandada pelo joystick, desconecte o cabo serial/USB ESP32 $\leftrightarrow$ RPi. Os motores devem parar em $\le 200\text{ ms}$ e `odometry_valid` deve ficar `false`.
4. **Conferência de Polaridade (Motores e KY-040):**
   - Comande avanço para frente no joystick. Ambas as rodas devem girar para frente e `odom_x` deve aumentar positivamente.
   - Se alguma roda ou encoder inverter o sinal, ajuste `invert_left_motor`, `invert_right_motor`, `invert_left_encoder` ou `invert_right_encoder` em [`src/agv_hardware/config/hardware_params.yaml`](file:///c:/Users/João%20Pedro/Documents/AGV/src/agv_hardware/config/hardware_params.yaml) e reinicie o container:
     ```bash
     docker compose -f docker-compose.rpi.yml restart
     ```
5. **Calibração no Piso:**
   - Meça `1,00 m` no chão e valide que `/odom` reporta `~1.00 m`. Ajuste `wheel_radius` ou `encoder_ticks_per_rev` se houver desvio sistemático.
   - Ajuste `dark_threshold` ou `hsv_lower/hsv_upper` em [`src/agv_brain/config/brain_params.yaml`](file:///c:/Users/João%20Pedro/Documents/AGV/src/agv_brain/config/brain_params.yaml) conforme a iluminação real do ambiente fabril.
