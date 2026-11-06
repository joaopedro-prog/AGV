# Catálogo de Tópicos, Serviços e Parâmetros ROS 2
**Versão:** 1.0 (Congelada na Fase 0)  
**Status:** Congelado / Mandatório  
**Autores:** Agent-Coordinator & Agent-QA-Safety-Auditor  

---

## 1. Topologia de Tópicos de Velocidade (`twist_mux`)

A arbitragem de movimento segue estritamente a configuração de prioridades definida em `src/articubot_one/config/twist_mux.yaml`:

| Tópico | Tipo de Mensagem | Prioridade | Timeout | Origem | Finalidade |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/cmd_vel_emergency` | `geometry_msgs/msg/Twist` | **255** | 0.5 s | Supervisor de Segurança / Dashboard | Parada de emergência por software e corte de movimento |
| `/cmd_vel_joy` | `geometry_msgs/msg/Twist` | **100** | 0.5 s | Teleoperação Joystick / Dashboard Virtual | Controle manual de operador humano com deadman switch |
| `/cmd_vel_line` | `geometry_msgs/msg/Twist` | **30** | 0.5 s | Nó seguidor de linha (`line_follower`) | Navegação autônoma guiada por visão |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | **10** | 0.5 s | Nav2 / Sistema Base / Standby | Navegação padrão de baixa prioridade |
| **`/diff_cont/cmd_vel_unstamped`** | `geometry_msgs/msg/Twist` | — | — | **Saída do `twist_mux`** | Comando arbitrado consumido pelo nó de atuadores (`serial_bridge` ou Gazebo) |

---

## 2. Tópicos de Telemetria e Diagnóstico

| Tópico | Tipo de Mensagem | Taxa Nominal | Origem | Finalidade |
| :--- | :--- | :--- | :--- | :--- |
| `/odom` | `nav_msgs/msg/Odometry` | 30 Hz | `serial_bridge` / Gazebo | Odometria calculada a partir dos encoders das rodas |
| `/scan` | `sensor_msgs/msg/LaserScan` | 10 Hz | `rplidar_ros` / Gazebo | Varredura de 360° do sensor LiDAR |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | 15–20 Hz | `v4l2_camera` / Gazebo | Imagem crua (320x240 na RPi 3B) |
| `/agv/line_error` | `geometry_msgs/msg/Vector3` | 15–20 Hz | `line_detector` | Erro lateral normalizado [-1.0..+1.0] e flag de linha visível |
| `/agv/state` | `std_msgs/msg/String` | 10 Hz | `line_follower` / Supervisor | Estado atual da máquina de estados do AGV |
| `/agv/battery_voltage`| `std_msgs/msg/Float32` | 2 Hz | `serial_bridge` | Tensão atual da bateria em Volts |
| `/agv/hardware_status`| `std_msgs/msg/String` (JSON) | 5 Hz | `serial_bridge` | Conexão serial, odometria válida e estado de emergência |
| `/agv/obstacle_detected`| `std_msgs/msg/Bool` | 10 Hz | `serial_bridge` / LiDAR | Flag de obstáculo frontal ativo |

---

## 3. Serviços ROS 2

| Serviço | Tipo de Serviço | Servidor | Finalidade |
| :--- | :--- | :--- | :--- |
| `/agv/set_following` | `std_srvs/srv/SetBool` | `line_follower` | Habilita (true) ou desabilita (false) o seguidor de linha |
| `/agv/reset_emergency`| `std_srvs/srv/Trigger` | `serial_bridge` | Executa o procedimento de rearme após parada de emergência física ou watchdog |
| `/agv/cmd_stop` | `std_srvs/srv/Trigger` | Supervisor | Solicita parada remota controlada do AGV |
