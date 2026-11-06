#!/usr/bin/env python3
"""
Nó Controlador PID Seguidor de Linha + Supervisor de Segurança do AGV.

Comportamento:
1. Inicia em IDLE (Parado) para segurança.
2. Suporta os 3 níveis de parada do contrato v1.0:
   - REMOTE_STOP_REQUESTED: aplica rampa de desaceleração controlada.
   - STOP_CONFIRMED: confirma velocidade zero nas rodas.
   - HARDWARE_ESTOP_ACTIVE: interrupção imediata por botão físico ou obstáculo.
3. Supervisor de Segurança com LiDAR 360 (/scan):
   - Monitora setor frontal de +-30 graus. Se houver obstáculo a menos de 0.40m,
     publica velocidade zero em /cmd_vel_emergency (Prioridade 255).
4. Controle PID suave com compensação de curvas para tração diferencial.
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool


class LineFollowerNode(Node):
    def __init__(self):
        super().__init__('line_follower')

        # Parâmetros dinâmicos
        self.declare_parameter('auto_start', False)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel_line')
        self.declare_parameter('base_linear_speed', 0.25)
        self.declare_parameter('min_linear_speed', 0.10)
        self.declare_parameter('max_angular_speed', 2.00)
        self.declare_parameter('curve_slowdown_factor', 0.60)
        self.declare_parameter('kp', 2.80)
        self.declare_parameter('ki', 0.00)
        self.declare_parameter('kd', 0.20)
        self.declare_parameter('search_on_lost_line', True)
        self.declare_parameter('search_linear_speed', 0.06)
        self.declare_parameter('search_angular_speed', 0.80)
        self.declare_parameter('max_lost_line_time_sec', 3.0)
        self.declare_parameter('lidar_stop_distance_m', 0.40)

        self.active: bool = bool(self.get_parameter('auto_start').value)
        cmd_vel_topic: str = self.get_parameter('cmd_vel_topic').value
        self.lidar_stop_dist: float = float(self.get_parameter('lidar_stop_distance_m').value)

        # Estado da máquina de estados
        self.state = 'IDLE' if not self.active else 'EM_MOVIMENTO'
        self.line_visible = False
        self.current_error = 0.0
        self.last_valid_error = 0.0
        self.prev_error = 0.0
        self.integral_error = 0.0

        self.obstacle_detected = False
        self.lidar_emergency = False
        self.decel_target_speed = 0.0
        self.current_cmd_speed = 0.0

        now = self.get_clock().now()
        self.last_control_time = now
        self.last_line_seen_time = now

        # Publishers
        self.cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
        self.emergency_pub = self.create_publisher(Twist, '/cmd_vel_emergency', 10)
        self.state_pub = self.create_publisher(String, '/agv/state', 10)

        # Subscribers
        self.error_sub = self.create_subscription(
            Vector3, '/agv/line_error', self.line_error_callback, 10
        )
        self.command_sub = self.create_subscription(
            String, '/agv/command', self.command_callback, 10
        )
        self.obstacle_sub = self.create_subscription(
            Bool, '/agv/obstacle_detected', self.obstacle_callback, 10
        )
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10
        )

        # Service
        self.srv = self.create_service(
            SetBool, '/agv/set_following', self.set_following_callback
        )

        # Loop de controle a 30 Hz
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)

        self.get_logger().info(
            f'LineFollowerNode v1.0 iniciado | Estado inicial: {self.state} | '
            f'LiDAR Safety Zone: {self.lidar_stop_dist}m'
        )

    def scan_callback(self, msg: LaserScan):
        """Avalia setor frontal +-30 graus do LiDAR 360."""
        angle_min = -math.radians(30)
        angle_max = math.radians(30)

        emergency = False
        for i, r in enumerate(msg.ranges):
            if math.isinf(r) or math.isnan(r) or r < msg.range_min or r > msg.range_max:
                continue

            angle = msg.angle_min + i * msg.angle_increment
            # Normaliza para [-pi, +pi]
            angle = (angle + math.pi) % (2.0 * math.pi) - math.pi

            if angle_min <= angle <= angle_max:
                if r < self.lidar_stop_dist:
                    emergency = True
                    break

        self.lidar_emergency = emergency
        if emergency:
            # Publica corte prioritário 255 no twist_mux
            e_twist = Twist()
            self.emergency_pub.publish(e_twist)

    def line_error_callback(self, msg: Vector3):
        self.line_visible = (msg.z > 0.5)
        if self.line_visible:
            self.current_error = float(msg.x)
            self.last_valid_error = self.current_error
            self.last_line_seen_time = self.get_clock().now()

    def obstacle_callback(self, msg: Bool):
        self.obstacle_detected = bool(msg.data)

    def command_callback(self, msg: String):
        cmd = msg.data.strip().upper()
        if cmd in ('START', 'GO', 'RUN'):
            self._request_start()
        elif cmd in ('STOP', 'IDLE', 'PAUSE'):
            self._request_stop()

    def set_following_callback(self, request: SetBool.Request, response: SetBool.Response):
        if request.data:
            self._request_start()
            response.success = True
            response.message = 'AGV ativado (START).'
        else:
            self._request_stop()
            response.success = True
            response.message = 'Parada solicitada (STOP).'
        return response

    def _request_start(self):
        if self.lidar_emergency or self.obstacle_detected:
            self.get_logger().warn('Comando START recusado: obstáculo na zona de segurança!')
            return
        self.active = True
        self.state = 'EM_MOVIMENTO'
        self.integral_error = 0.0
        self.prev_error = 0.0
        self.last_line_seen_time = self.get_clock().now()
        self.get_logger().info('>>> AGV EM MOVIMENTO (Seguindo Linha) <<<')

    def _request_stop(self):
        self.active = False
        self.state = 'REMOTE_STOP_REQUESTED'
        self.get_logger().info('>>> PARADA REMOTA SOLICITADA (Desacelerando...) <<<')

    def _publish_zero(self):
        t = Twist()
        self.cmd_pub.publish(t)
        self.current_cmd_speed = 0.0

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_control_time).nanoseconds / 1e9
        self.last_control_time = now
        if dt <= 0.0 or dt > 0.5:
            dt = 1.0 / 30.0

        # Publica estado atual
        s_msg = String()
        s_msg.data = self.state
        self.state_pub.publish(s_msg)

        # 1. Trata Emergência de Obstáculo (LiDAR ou Ultrassom)
        if self.lidar_emergency or self.obstacle_detected:
            self._publish_zero()
            self.state = 'HARDWARE_ESTOP_ACTIVE'
            return

        # 2. Trata Parada Solicitada (Rampa de Desaceleração)
        if self.state == 'REMOTE_STOP_REQUESTED':
            if self.current_cmd_speed > 0.02:
                self.current_cmd_speed = max(0.0, self.current_cmd_speed - 0.5 * dt)
                t = Twist()
                t.linear.x = self.current_cmd_speed
                self.cmd_pub.publish(t)
            else:
                self._publish_zero()
                self.state = 'STOP_CONFIRMED'
                self.get_logger().info('>>> PARADA CONFIRMADA (Robô Imobilizado) <<<')
            return

        # 3. Estado IDLE ou STOP_CONFIRMED
        if not self.active:
            self._publish_zero()
            return

        # 4. Controle PID quando em movimento
        time_lost = (now - self.last_line_seen_time).nanoseconds / 1e9
        max_lost_time = float(self.get_parameter('max_lost_line_time_sec').value)

        twist = Twist()
        base_speed = float(self.get_parameter('base_linear_speed').value)
        min_speed = float(self.get_parameter('min_linear_speed').value)
        max_ang = float(self.get_parameter('max_angular_speed').value)
        slowdown = float(self.get_parameter('curve_slowdown_factor').value)
        kp = float(self.get_parameter('kp').value)
        kd = float(self.get_parameter('kd').value)

        if self.line_visible:
            # PID sobre o erro lateral
            err = self.current_error
            deriv = (err - self.prev_error) / dt
            self.prev_error = err

            w_cmd = -(kp * err + kd * deriv)
            w_cmd = max(-max_ang, min(max_ang, w_cmd))

            # Desacelera em curvas
            err_abs = min(1.0, abs(err))
            v_cmd = max(min_speed, base_speed * (1.0 - err_abs * slowdown))

            twist.linear.x = v_cmd
            twist.angular.z = w_cmd
            self.current_cmd_speed = v_cmd
        else:
            # Busca ativa suave
            if time_lost > max_lost_time:
                self._publish_zero()
                self.state = 'LOST_LINE_STOPPED'
                return
            twist.linear.x = float(self.get_parameter('search_linear_speed').value)
            turn_dir = 1.0 if self.last_valid_error < 0.0 else -1.0
            twist.angular.z = turn_dir * float(self.get_parameter('search_angular_speed').value)

        self.cmd_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = LineFollowerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
