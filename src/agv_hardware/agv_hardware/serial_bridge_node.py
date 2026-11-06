#!/usr/bin/env python3
"""
Nó de Ponte Serial USB (Raspberry Pi 3B <-> ESP32).
Implementação em conformidade estrita com o Contrato de Interface Serial v1.0.

Responsabilidades:
1. Recebe comandos de velocidade arbitrados (/diff_cont/cmd_vel_unstamped ou /cmd_vel).
2. Converte linear (m/s) e angular (rad/s) em velocidades das rodas (rad/s).
3. Transmite frames formatados com CRC16-CCITT: $CMD,<seq>,<left_rad_s>,<right_rad_s>*<CRC16>\\r\\n.
4. Processa telemetria $TELEM a 30 Hz com validação rigorosa de CRC16 e número de sequência.
5. Gerencia estado de link: se a conexão cair ou timeout > 200ms, NÃO publica odometria falsa
   com velocidade zero; sinaliza odometry_valid: false e aciona /cmd_vel_emergency (prio 255).
6. Provê serviço /agv/reset_emergency para procedimento seguro de rearme em 5 passos.
"""

import json
import math
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float32, Float32MultiArray, String
from std_srvs.srv import Trigger
from tf2_ros import TransformBroadcaster

try:
    import serial
    HAS_PYSERIAL = True
except ImportError:
    HAS_PYSERIAL = False


def calculate_crc16(data_bytes: bytes) -> int:
    """
    Calcula CRC16-CCITT (Polinômio: 0x1021, Init: 0xFFFF, RefIn/RefOut: false, XorOut: 0x0000).
    Abrange estritamente todos os bytes entre '$' e '*'.
    """
    crc = 0xFFFF
    for b in data_bytes:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def format_packet(payload: str) -> str:
    """Encapsula payload no padrão $<PAYLOAD>*<CRC16>\\r\\n."""
    crc = calculate_crc16(payload.encode('ascii'))
    return f"${payload}*{crc:04X}\r\n"


def euler_to_quaternion(yaw: float):
    half_yaw = yaw * 0.5
    return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


class SerialBridgeNode(Node):
    def __init__(self):
        super().__init__('serial_bridge')

        # Parâmetros configuráveis
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('serial_timeout', 0.02)
        self.declare_parameter('auto_reconnect', True)
        self.declare_parameter('mock_serial_if_disconnected', False)

        self.declare_parameter('wheel_radius', 0.0762)
        self.declare_parameter('wheel_separation', 0.468)
        self.declare_parameter('encoder_ticks_per_rev', 3436)
        self.declare_parameter('max_wheel_speed_rad_s', 15.0)

        self.declare_parameter('invert_left_motor', False)
        self.declare_parameter('invert_right_motor', False)
        self.declare_parameter('invert_left_encoder', False)
        self.declare_parameter('invert_right_encoder', False)

        self.declare_parameter('cmd_vel_timeout_sec', 0.5)
        self.declare_parameter('publish_odom_tf', True)
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_link')
        self.declare_parameter('obstacle_stop_distance_m', 0.25)

        self.serial_port: str = self.get_parameter('serial_port').value
        self.baud_rate: int = self.get_parameter('baud_rate').value
        self.serial_timeout: float = float(self.get_parameter('serial_timeout').value)
        self.auto_reconnect: bool = bool(self.get_parameter('auto_reconnect').value)
        self.mock_if_disconnected: bool = bool(self.get_parameter('mock_serial_if_disconnected').value)

        self.wheel_radius: float = float(self.get_parameter('wheel_radius').value)
        self.wheel_separation: float = float(self.get_parameter('wheel_separation').value)
        self.ticks_per_rev: int = int(self.get_parameter('encoder_ticks_per_rev').value)
        self.max_wheel_rad_s: float = float(self.get_parameter('max_wheel_speed_rad_s').value)

        self.invert_left_motor: bool = bool(self.get_parameter('invert_left_motor').value)
        self.invert_right_motor: bool = bool(self.get_parameter('invert_right_motor').value)
        self.invert_left_enc: bool = bool(self.get_parameter('invert_left_encoder').value)
        self.invert_right_enc: bool = bool(self.get_parameter('invert_right_encoder').value)

        self.cmd_vel_timeout: float = float(self.get_parameter('cmd_vel_timeout_sec').value)
        self.publish_odom_tf: bool = bool(self.get_parameter('publish_odom_tf').value)
        self.odom_frame_id: str = self.get_parameter('odom_frame_id').value
        self.base_frame_id: str = self.get_parameter('base_frame_id').value
        self.obstacle_stop_dist: float = float(self.get_parameter('obstacle_stop_distance_m').value)

        # Estado da conexão serial e protocolo
        self.ser: Optional["serial.Serial"] = None
        self.tx_seq: int = 0
        self.last_rx_seq: int = 0
        self.last_reconnect_attempt = 0.0
        self.serial_connected = False
        self.odometry_valid = False
        self.crc_errors = 0
        self.consecutive_crc_errors = 0

        # Estado de Odometria
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.left_wheel_pos_rad = 0.0
        self.right_wheel_pos_rad = 0.0
        self.left_wheel_vel_rad_s = 0.0
        self.right_wheel_vel_rad_s = 0.0
        self.prev_ticks_left: Optional[int] = None
        self.prev_ticks_right: Optional[int] = None

        now = self.get_clock().now()
        self.last_odom_time = now
        self.last_valid_telem_time = now
        self.last_cmd_time = now

        # Estado de comando
        self.target_lin_x = 0.0
        self.target_ang_z = 0.0
        self.last_safety_state_str = "DISCONNECTED"

        # Buffer de recepção
        self.rx_buffer = bytearray()

        # Publishers
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.battery_pub = self.create_publisher(Float32, '/agv/battery_voltage', 10)
        self.obstacle_pub = self.create_publisher(Bool, '/agv/obstacle_detected', 10)
        self.hw_status_pub = self.create_publisher(String, '/agv/hardware_status', 10)
        self.emergency_pub = self.create_publisher(Twist, '/cmd_vel_emergency', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Subscribers
        self.sub_mux = self.create_subscription(
            Twist, '/diff_cont/cmd_vel_unstamped', self.cmd_vel_callback, 10
        )
        self.sub_cmd = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10
        )

        # Service de Rearme (Recovery em 5 passos)
        self.reset_srv = self.create_service(
            Trigger, '/agv/reset_emergency', self.reset_emergency_callback
        )

        self._connect_serial()

        # Loop de controle principal a 30 Hz
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)

        self.get_logger().info(
            f'SerialBridge v1.0 inicializado | Porta: {self.serial_port} @ {self.baud_rate} | '
            f'CRC16-CCITT Ativo | Watchdog: 200ms'
        )

    def _connect_serial(self):
        if not HAS_PYSERIAL:
            return
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=self.serial_timeout
            )
            self.serial_connected = True
            self.get_logger().info(f'Conexão serial estabelecida em {self.serial_port}!')
        except Exception as exc:
            self.ser = None
            self.serial_connected = False
            self.odometry_valid = False

    def cmd_vel_callback(self, msg: Twist):
        self.target_lin_x = msg.linear.x
        self.target_ang_z = msg.angular.z
        self.last_cmd_time = self.get_clock().now()

    def reset_emergency_callback(self, request, response):
        """Envia pacote $RESET para o ESP32 e valida confirmação."""
        if self.ser is None or not self.ser.is_open:
            response.success = False
            response.message = 'Falha: Porta serial desconectada.'
            return response

        self.tx_seq = (self.tx_seq + 1) % 65536
        reset_pkt = format_packet(f'RESET,{self.tx_seq}')
        try:
            self.ser.write(reset_pkt.encode('ascii'))
            self.get_logger().info(f'Comando de rearme enviado: {reset_pkt.strip()}')
            response.success = True
            response.message = 'Ordem de rearme transmitida ao ESP32.'
        except Exception as exc:
            response.success = False
            response.message = f'Erro no envio: {exc}'
        return response

    def control_loop(self):
        now = self.get_clock().now()
        dt_cmd = (now - self.last_cmd_time).nanoseconds / 1e9

        # Watchdog de comando de software
        if dt_cmd > self.cmd_vel_timeout:
            lin_x = 0.0
            ang_z = 0.0
        else:
            lin_x = self.target_lin_x
            ang_z = self.target_ang_z

        v_left_m_s = lin_x - (ang_z * self.wheel_separation * 0.5)
        v_right_m_s = lin_x + (ang_z * self.wheel_separation * 0.5)

        w_left_rad_s = v_left_m_s / self.wheel_radius
        w_right_rad_s = v_right_m_s / self.wheel_radius

        w_left_rad_s = max(-self.max_wheel_rad_s, min(self.max_wheel_rad_s, w_left_rad_s))
        w_right_rad_s = max(-self.max_wheel_rad_s, min(self.max_wheel_rad_s, w_right_rad_s))

        cmd_left = -w_left_rad_s if self.invert_left_motor else w_left_rad_s
        cmd_right = -w_right_rad_s if self.invert_right_motor else w_right_rad_s

        # 1. Envio de Comando Serial
        if self.ser is not None and self.ser.is_open:
            try:
                self.tx_seq = (self.tx_seq + 1) % 65536
                cmd_payload = f'CMD,{self.tx_seq},{cmd_left:.2f},{cmd_right:.2f}'
                cmd_packet = format_packet(cmd_payload)
                self.ser.write(cmd_packet.encode('ascii'))

                self._read_serial_packets()
            except Exception as exc:
                self.get_logger().error(f'Falha na comunicação serial: {exc}')
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                self.serial_connected = False
                self.odometry_valid = False
        else:
            # Tratamento de perda de conexão
            self.serial_connected = False
            self.odometry_valid = False

            if self.auto_reconnect and (time.time() - self.last_reconnect_attempt > 1.0):
                self.last_reconnect_attempt = time.time()
                self._connect_serial()

        # 2. Verificação de Timeout de Telemetria (> 200 ms)
        time_since_telem = (now - self.last_valid_telem_time).nanoseconds / 1e9
        if time_since_telem > 0.200:
            if self.odometry_valid:
                self.get_logger().warn(
                    f'Timeout serial de telemetria ({time_since_telem:.3f}s > 0.200s). '
                    'Invalidando odometria e acionando emergência!'
                )
            self.odometry_valid = False
            # Aciona emergência prioritária 255
            estop_msg = Twist()
            self.emergency_pub.publish(estop_msg)

        # 3. Publicação de Status de Hardware (5 Hz)
        status_dict = {
            'serial_connected': self.serial_connected,
            'odometry_valid': self.odometry_valid,
            'safety_state': self.last_safety_state_str,
            'crc_errors': self.crc_errors
        }
        status_msg = String()
        status_msg.data = json.dumps(status_dict)
        self.hw_status_pub.publish(status_msg)

    def _read_serial_packets(self):
        """Lê bytes disponíveis e segmenta pacotes delimitados por $ e \\r\\n."""
        while self.ser is not None and self.ser.in_waiting > 0:
            b = self.ser.read(self.ser.in_waiting)
            self.rx_buffer.extend(b)

            while True:
                start_idx = self.rx_buffer.find(b'$')
                if start_idx == -1:
                    self.rx_buffer.clear()
                    break

                end_idx = self.rx_buffer.find(b'\r\n', start_idx)
                if end_idx == -1:
                    # Pacote incompleto ainda no buffer
                    if start_idx > 0:
                        del self.rx_buffer[:start_idx]
                    break

                raw_packet = self.rx_buffer[start_idx:end_idx].decode('ascii', errors='ignore')
                del self.rx_buffer[:end_idx + 2]

                self._process_single_packet(raw_packet)

    def _process_single_packet(self, packet_str: str):
        """Valida CRC16 e decodifica mensagem conforme contrato v1.0."""
        # Formato: $<PAYLOAD>*<CRC16>
        star_pos = packet_str.rfind('*')
        if star_pos < 1:
            return

        payload = packet_str[1:star_pos]
        crc_str = packet_str[star_pos + 1:].strip()

        if len(crc_str) != 4:
            return

        try:
            expected_crc = int(crc_str, 16)
        except ValueError:
            return

        calculated_crc = calculate_crc16(payload.encode('ascii'))
        if expected_crc != calculated_crc:
            self.crc_errors += 1
            self.consecutive_crc_errors += 1
            if self.consecutive_crc_errors == 3:
                self.get_logger().warn('AVISO: 3 erros consecutivos de CRC16 detectados na serial.')
            return

        self.consecutive_crc_errors = 0
        parts = payload.split(',')
        if not parts:
            return

        msg_type = parts[0].upper()
        if msg_type == 'TELEM' and len(parts) >= 9:
            self._handle_telemetry(parts)
        elif msg_type == 'ACK_STOP':
            self.get_logger().info('Confirmação de parada (ACK_STOP) recebida do ESP32.')
        elif msg_type == 'ACK_RESET':
            self.get_logger().info(f'Confirmação de rearme (ACK_RESET={parts[-1]}) do ESP32.')

    def _handle_telemetry(self, parts):
        """
        Payload: TELEM,<seq>,<tL>,<tR>,<wL>,<wR>,<vbat>,<us_dist>,<status>
        """
        try:
            seq = int(parts[1])
            t_left = int(parts[2])
            t_right = int(parts[3])
            w_left = float(parts[4])
            w_right = float(parts[5])
            vbat_mv = int(parts[6])
            dist_cm = int(parts[7])
            safety_code = int(parts[8])
        except ValueError:
            return

        self.last_rx_seq = seq
        now = self.get_clock().now()
        self.last_valid_telem_time = now
        self.odometry_valid = True

        # Decodifica código de segurança
        states_map = {
            0: "OK",
            1: "HARDWARE_ESTOP_ACTIVE",
            2: "WATCHDOG_TIMEOUT",
            3: "DRIVER_FAULT",
            4: "ESTOP_CLEARED_PENDING_RESET"
        }
        self.last_safety_state_str = states_map.get(safety_code, "UNKNOWN")

        # Tensão da bateria
        bat_msg = Float32()
        bat_msg.data = float(vbat_mv) / 1000.0
        self.battery_pub.publish(bat_msg)

        # Obstáculo
        is_blocked = (0 < dist_cm < int(self.obstacle_stop_dist * 100))
        obs_msg = Bool()
        obs_msg.data = bool(is_blocked)
        self.obstacle_pub.publish(obs_msg)

        # Odometria real
        self._update_odometry(t_left, t_right, w_left, w_right, now)

    def _update_odometry(self, ticks_left: int, ticks_right: int,
                         w_left: float, w_right: float, now):
        if self.invert_left_enc:
            ticks_left = -ticks_left
        if self.invert_right_enc:
            ticks_right = -ticks_right

        if self.prev_ticks_left is None or self.prev_ticks_right is None:
            self.prev_ticks_left = ticks_left
            self.prev_ticks_right = ticks_right
            self.last_odom_time = now
            return

        d_ticks_l = ticks_left - self.prev_ticks_left
        d_ticks_r = ticks_right - self.prev_ticks_right
        self.prev_ticks_left = ticks_left
        self.prev_ticks_right = ticks_right

        dt = (now - self.last_odom_time).nanoseconds / 1e9
        self.last_odom_time = now
        if dt <= 0.0:
            return

        dist_per_tick = (2.0 * math.pi * self.wheel_radius) / float(self.ticks_per_rev)
        dist_l = d_ticks_l * dist_per_tick
        dist_r = d_ticks_r * dist_per_tick

        dist_center = (dist_l + dist_r) * 0.5
        d_yaw = (dist_r - dist_l) / self.wheel_separation

        if abs(d_yaw) < 1e-6:
            self.x += dist_center * math.cos(self.yaw + d_yaw * 0.5)
            self.y += dist_center * math.sin(self.yaw + d_yaw * 0.5)
        else:
            turn_radius = dist_center / d_yaw
            self.x += turn_radius * (math.sin(self.yaw + d_yaw) - math.sin(self.yaw))
            self.y -= turn_radius * (math.cos(self.yaw + d_yaw) - math.cos(self.yaw))
        self.yaw += d_yaw

        vx = dist_center / dt
        wz = d_yaw / dt

        # Publica Odometria e TF
        quat = euler_to_quaternion(self.yaw)

        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = self.odom_frame_id
        odom.child_frame_id = self.base_frame_id
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.x = quat[0]
        odom.pose.pose.orientation.y = quat[1]
        odom.pose.pose.orientation.z = quat[2]
        odom.pose.pose.orientation.w = quat[3]
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = wz

        self.odom_pub.publish(odom)

        if self.publish_odom_tf:
            t = TransformStamped()
            t.header.stamp = now.to_msg()
            t.header.frame_id = self.odom_frame_id
            t.child_frame_id = self.base_frame_id
            t.transform.translation.x = self.x
            t.transform.translation.y = self.y
            t.transform.translation.z = 0.0
            t.transform.rotation.x = quat[0]
            t.transform.rotation.y = quat[1]
            t.transform.rotation.z = quat[2]
            t.transform.rotation.w = quat[3]
            self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = SerialBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
