#!/usr/bin/env python3
"""
Nó de Ponte Serial USB (Raspberry Pi <-> Microcontrolador).

Responsabilidades:
1. Recebe comandos de velocidade (/cmd_vel e /diff_cont/cmd_vel_unstamped).
2. Converte velocidade linear (m/s) e angular (rad/s) em velocidades das rodas
   esquerda e direita usando as constantes físicas do robô.
3. Envia comandos via USB Serial para o microcontrolador (Arduino/ESP32/STM32).
4. Lê os pulsos de encoder (ENC,esq,dir) e sensores extras (SENS,dist,bat,...)
   vindos do microcontrolador via Serial.
5. Calcula e publica Odometria (/odom), TF (odom -> base_link), estados das
   rodas (/joint_states) e sensores (/agv/mcu_sensors, /agv/obstacle_detected).
"""

import math
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, Float32, Float32MultiArray
from tf2_ros import TransformBroadcaster

try:
    import serial
    HAS_PYSERIAL = True
except ImportError:
    HAS_PYSERIAL = False


def euler_to_quaternion(yaw: float):
    """Converte ângulo yaw (rad) em quaternion (x, y, z, w)."""
    half_yaw = yaw * 0.5
    return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


class SerialBridgeNode(Node):
    def __init__(self):
        super().__init__('serial_bridge')

        # Declaração de parâmetros (carregados do hardware_params.yaml)
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('serial_timeout', 0.05)
        self.declare_parameter('auto_reconnect', True)
        self.declare_parameter('mock_serial_if_disconnected', True)

        self.declare_parameter('wheel_radius', 0.0762)
        self.declare_parameter('wheel_separation', 0.468)
        self.declare_parameter('encoder_ticks_per_rev', 3436)
        self.declare_parameter('max_wheel_speed_rad_s', 15.0)

        self.declare_parameter('invert_left_motor', False)
        self.declare_parameter('invert_right_motor', False)
        self.declare_parameter('invert_left_encoder', False)
        self.declare_parameter('invert_right_encoder', False)

        self.declare_parameter('command_format', 'wheel_rad_s')
        self.declare_parameter('cmd_vel_timeout_sec', 0.5)
        self.declare_parameter('publish_odom_tf', True)
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_link')
        self.declare_parameter('obstacle_stop_distance_m', 0.25)

        # Leitura dos parâmetros
        self.serial_port: str = self.get_parameter('serial_port').value
        self.baud_rate: int = self.get_parameter('baud_rate').value
        self.serial_timeout: float = self.get_parameter('serial_timeout').value
        self.auto_reconnect: bool = self.get_parameter('auto_reconnect').value
        self.mock_if_disconnected: bool = self.get_parameter('mock_serial_if_disconnected').value

        self.wheel_radius: float = float(self.get_parameter('wheel_radius').value)
        self.wheel_separation: float = float(self.get_parameter('wheel_separation').value)
        self.ticks_per_rev: int = int(self.get_parameter('encoder_ticks_per_rev').value)
        self.max_wheel_rad_s: float = float(self.get_parameter('max_wheel_speed_rad_s').value)

        self.invert_left_motor: bool = self.get_parameter('invert_left_motor').value
        self.invert_right_motor: bool = self.get_parameter('invert_right_motor').value
        self.invert_left_enc: bool = self.get_parameter('invert_left_encoder').value
        self.invert_right_enc: bool = self.get_parameter('invert_right_encoder').value

        self.command_format: str = self.get_parameter('command_format').value
        self.cmd_vel_timeout: float = float(self.get_parameter('cmd_vel_timeout_sec').value)
        self.publish_odom_tf: bool = self.get_parameter('publish_odom_tf').value
        self.odom_frame_id: str = self.get_parameter('odom_frame_id').value
        self.base_frame_id: str = self.get_parameter('base_frame_id').value
        self.obstacle_stop_dist: float = float(self.get_parameter('obstacle_stop_distance_m').value)

        # Estado interno de Odometria
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.left_wheel_pos_rad = 0.0
        self.right_wheel_pos_rad = 0.0
        self.left_wheel_vel_rad_s = 0.0
        self.right_wheel_vel_rad_s = 0.0

        self.prev_ticks_left: Optional[int] = None
        self.prev_ticks_right: Optional[int] = None
        self.last_odom_time = self.get_clock().now()

        # Estado de comando atual
        self.target_lin_x = 0.0
        self.target_ang_z = 0.0
        self.last_cmd_time = self.get_clock().now()

        # Conexão Serial
        self.ser: Optional["serial.Serial"] = None
        self.last_reconnect_attempt = 0.0
        self.warned_mock = False
        self._connect_serial()

        # Publishers
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.mcu_sensors_pub = self.create_publisher(Float32MultiArray, '/agv/mcu_sensors', 10)
        self.battery_pub = self.create_publisher(Float32, '/agv/battery_voltage', 10)
        self.obstacle_pub = self.create_publisher(Bool, '/agv/obstacle_detected', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Subscribers (escuta tanto a saída do twist_mux quanto /cmd_vel direto)
        self.sub_mux = self.create_subscription(
            Twist, '/diff_cont/cmd_vel_unstamped', self.cmd_vel_callback, 10
        )
        self.sub_cmd = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10
        )

        # Loop principal a 30 Hz (envio de comandos, leitura serial e publicação de odometria)
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)

        self.get_logger().info(
            f'SerialBridge iniciado | Porta: {self.serial_port} @ {self.baud_rate} bps | '
            f'R_roda: {self.wheel_radius}m | L_eixo: {self.wheel_separation}m'
        )

    def _connect_serial(self):
        """Tenta abrir a porta serial com o microcontrolador."""
        if not HAS_PYSERIAL:
            if not self.warned_mock:
                self.get_logger().warn(
                    'Biblioteca pyserial não encontrada. Rodando em modo simulado de porta serial.'
                )
                self.warned_mock = True
            return

        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=self.serial_timeout
            )
            self.get_logger().info(f'Conectado com sucesso ao microcontrolador em {self.serial_port}!')
            self.warned_mock = False
        except Exception as exc:
            self.ser = None
            if not self.warned_mock:
                self.get_logger().warn(
                    f'Não foi possível abrir {self.serial_port} ({exc}). '
                    f'Modo Mock Ativo={self.mock_if_disconnected}. Aguardando conexão física...'
                )
                self.warned_mock = True

    def cmd_vel_callback(self, msg: Twist):
        """Recebe comandos de velocidade linear e angular."""
        self.target_lin_x = msg.linear.x
        self.target_ang_z = msg.angular.z
        self.last_cmd_time = self.get_clock().now()

    def control_loop(self):
        """Ciclo periódico: aplica watchdog, envia comando serial, lê encoders/sensores e publica TF/Odom."""
        now = self.get_clock().now()
        dt_cmd = (now - self.last_cmd_time).nanoseconds / 1e9

        # Watchdog: zera velocidades se parou de receber comando
        if dt_cmd > self.cmd_vel_timeout:
            lin_x = 0.0
            ang_z = 0.0
        else:
            lin_x = self.target_lin_x
            ang_z = self.target_ang_z

        # Cinemática inversa diferencial:
        # v_left = v - (w * L / 2)
        # v_right = v + (w * L / 2)
        v_left_m_s = lin_x - (ang_z * self.wheel_separation * 0.5)
        v_right_m_s = lin_x + (ang_z * self.wheel_separation * 0.5)

        w_left_rad_s = v_left_m_s / self.wheel_radius
        w_right_rad_s = v_right_m_s / self.wheel_radius

        # Limita velocidade máxima
        w_left_rad_s = max(-self.max_wheel_rad_s, min(self.max_wheel_rad_s, w_left_rad_s))
        w_right_rad_s = max(-self.max_wheel_rad_s, min(self.max_wheel_rad_s, w_right_rad_s))

        # Aplica inversão de sentido se configurado
        cmd_left = -w_left_rad_s if self.invert_left_motor else w_left_rad_s
        cmd_right = -w_right_rad_s if self.invert_right_motor else w_right_rad_s

        # 1. Envia comando e lê telemetria se conectado na serial real
        if self.ser is not None and self.ser.is_open:
            try:
                if self.command_format == 'twist':
                    payload = f'V:{lin_x:.3f},W:{ang_z:.3f}\n'
                elif self.command_format == 'wheel_m_s':
                    payload = f'CMD,{v_left_m_s:.3f},{v_right_m_s:.3f}\n'
                else:
                    payload = f'CMD,{cmd_left:.3f},{cmd_right:.3f}\n'

                self.ser.write(payload.encode('utf-8'))
                self._read_serial_lines()
            except Exception as exc:
                self.get_logger().error(f'Erro na comunicação serial: {exc}')
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
        else:
            # Tenta reconectar a cada 3 segundos se auto_reconnect=True
            if self.auto_reconnect and (time.time() - self.last_reconnect_attempt > 3.0):
                self.last_reconnect_attempt = time.time()
                self._connect_serial()

            # Se estiver desconectado e mock_serial_if_disconnected=True, integra odometria ideal
            if self.mock_if_disconnected:
                dt = (now - self.last_odom_time).nanoseconds / 1e9
                if dt > 0.0:
                    self._update_odometry_from_displacement(
                        v_left_m_s * dt, v_right_m_s * dt, dt, now
                    )
                self.last_odom_time = now

    def _read_serial_lines(self):
        """
        Lê todas as linhas disponíveis no buffer serial enviadas pelo microcontrolador.
        Formatos aceitos do microcontrolador:
          - ENC,<ticks_esquerda>,<ticks_direita>
          - SENS,<distancia_obstaculo_m>,<tensao_bateria_v>,<sensor_extra_1>,...
        """
        while self.ser is not None and self.ser.in_waiting > 0:
            raw_line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not raw_line:
                continue

            parts = raw_line.split(',')
            header = parts[0].upper()

            if header == 'ENC' and len(parts) >= 3:
                try:
                    ticks_l = int(parts[1])
                    ticks_r = int(parts[2])
                    self._process_encoder_ticks(ticks_l, ticks_r)
                except ValueError:
                    pass

            elif header == 'SENS' and len(parts) >= 2:
                try:
                    values = [float(x) for x in parts[1:]]
                    arr_msg = Float32MultiArray()
                    arr_msg.data = values
                    self.mcu_sensors_pub.publish(arr_msg)

                    # Primeiro valor: distância do sensor de obstáculo frontal (em metros)
                    dist_m = values[0]
                    is_blocked = (0.0 < dist_m < self.obstacle_stop_dist)
                    obs_msg = Bool()
                    obs_msg.data = bool(is_blocked)
                    self.obstacle_pub.publish(obs_msg)

                    # Segundo valor (se existir): tensão da bateria (Volts)
                    if len(values) >= 2:
                        bat_msg = Float32()
                        bat_msg.data = values[1]
                        self.battery_pub.publish(bat_msg)
                except ValueError:
                    pass

    def _process_encoder_ticks(self, ticks_left: int, ticks_right: int):
        """Converte variação de pulsos acumulados dos encoders em deslocamento métrico."""
        if self.invert_left_enc:
            ticks_left = -ticks_left
        if self.invert_right_enc:
            ticks_right = -ticks_right

        now = self.get_clock().now()
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

        meters_per_tick = (2.0 * math.pi * self.wheel_radius) / float(self.ticks_per_rev)
        dist_left = d_ticks_l * meters_per_tick
        dist_right = d_ticks_r * meters_per_tick

        self._update_odometry_from_displacement(dist_left, dist_right, dt, now)

    def _update_odometry_from_displacement(self, dist_left: float, dist_right: float, dt: float, now):
        """Atualiza pose (x, y, yaw) e publica /odom, TF e /joint_states."""
        dist_center = 0.5 * (dist_left + dist_right)
        delta_yaw = (dist_right - dist_left) / self.wheel_separation

        # Integração Runge-Kutta de 2ª ordem (ponto médio)
        mid_yaw = self.yaw + 0.5 * delta_yaw
        self.x += dist_center * math.cos(mid_yaw)
        self.y += dist_center * math.sin(mid_yaw)
        self.yaw = math.atan2(math.sin(self.yaw + delta_yaw), math.cos(self.yaw + delta_yaw))

        lin_vel = dist_center / dt if dt > 0.0 else 0.0
        ang_vel = delta_yaw / dt if dt > 0.0 else 0.0

        # Atualiza ângulos das rodas para o JointState
        d_angle_l = dist_left / self.wheel_radius
        d_angle_r = dist_right / self.wheel_radius
        self.left_wheel_pos_rad += d_angle_l
        self.right_wheel_pos_rad += d_angle_r
        self.left_wheel_vel_rad_s = d_angle_l / dt if dt > 0.0 else 0.0
        self.right_wheel_vel_rad_s = d_angle_r / dt if dt > 0.0 else 0.0

        qx, qy, qz, qw = euler_to_quaternion(self.yaw)
        stamp = now.to_msg()

        # 1. Publica TF (odom -> base_link)
        if self.publish_odom_tf:
            t = TransformStamped()
            t.header.stamp = stamp
            t.header.frame_id = self.odom_frame_id
            t.child_frame_id = self.base_frame_id
            t.transform.translation.x = self.x
            t.transform.translation.y = self.y
            t.transform.translation.z = 0.0
            t.transform.rotation.x = qx
            t.transform.rotation.y = qy
            t.transform.rotation.z = qz
            t.transform.rotation.w = qw
            self.tf_broadcaster.sendTransform(t)

        # 2. Publica mensagem /odom
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.odom_frame_id
        odom.child_frame_id = self.base_frame_id
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = lin_vel
        odom.twist.twist.angular.z = ang_vel
        self.odom_pub.publish(odom)

        # 3. Publica /joint_states para atualizar as rodas no RViz
        js = JointState()
        js.header.stamp = stamp
        js.name = ['left_wheel_joint', 'right_wheel_joint']
        js.position = [self.left_wheel_pos_rad, self.right_wheel_pos_rad]
        js.velocity = [self.left_wheel_vel_rad_s, self.right_wheel_vel_rad_s]
        self.joint_pub.publish(js)


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
