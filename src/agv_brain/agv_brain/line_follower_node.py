#!/usr/bin/env python3
"""
Nó Controlador PID Seguidor de Linha + Supervisor Ultrassônico do AGV.

Comportamento:
1. Inicia em IDLE (Parado) para segurança.
2. Segue a máquina de estados do contrato v1.0:
   - HARDWARE_ESTOP_ACTIVE / RECOVERY_PENDING: reservado para botão físico
     de emergência (ESP32 GPIO 33), Watchdog 200ms ou botão E-STOP do Dashboard.
   - REMOTE_STOP_REQUESTED / STOP_CONFIRMED: parada controlada por rampa.
3. Supervisor dos 2x Sensores Ultrassônicos Frontais (HC-SR04):
   - Monitora /agv/ultrasonic_left, /agv/ultrasonic_right e /agv/obstacle_detected.
   - Se stop_on_obstacle=True e um obstáculo entrar na zona crítica (< 0.25m),
     pausa o movimento de seguidor de linha até o caminho desobstruir (sem travar
     o robô em emergência física permanente).
4. Controle PID suave com compensação de curvas para tração diferencial.
"""

import json
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from sensor_msgs.msg import Range
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
        self.declare_parameter('stop_on_obstacle', True)
        self.declare_parameter('ultrasonic_stop_distance_m', 0.25)

        self.active: bool = bool(self.get_parameter('auto_start').value)
        cmd_vel_topic: str = self.get_parameter('cmd_vel_topic').value
        self.stop_on_obstacle: bool = bool(self.get_parameter('stop_on_obstacle').value)
        self.us_stop_dist: float = float(self.get_parameter('ultrasonic_stop_distance_m').value)

        # Estado da máquina de estados
        self.state = 'IDLE' if not self.active else 'EM_MOVIMENTO'
        self.line_visible = False
        self.current_error = 0.0
        self.last_valid_error = 0.0
        self.prev_error = 0.0
        self.integral_error = 0.0

        self.us_left_dist = float('inf')
        self.us_right_dist = float('inf')
        self.obstacle_flag = False
        self.hw_safety_state = 'INIT'
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
        self.us_left_sub = self.create_subscription(
            Range, '/agv/ultrasonic_left', self.us_left_callback, 10
        )
        self.us_right_sub = self.create_subscription(
            Range, '/agv/ultrasonic_right', self.us_right_callback, 10
        )
        self.hw_status_sub = self.create_subscription(
            String, '/agv/hardware_status', self.hw_status_callback, 10
        )

        # Service
        self.srv = self.create_service(
            SetBool, '/agv/set_following', self.set_following_callback
        )

        # Loop de controle a 30 Hz
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)

        self.get_logger().info(
            f'LineFollowerNode iniciado | Estado: {self.state} | '
            f'Ultrassônicos 2x HC-SR04 (corte={self.us_stop_dist:.2f}m, ativo={self.stop_on_obstacle})'
        )

    def us_left_callback(self, msg: Range):
        self.us_left_dist = float(msg.range) if not math.isnan(msg.range) else float('inf')

    def us_right_callback(self, msg: Range):
        self.us_right_dist = float(msg.range) if not math.isnan(msg.range) else float('inf')

    def _is_ultrasonic_blocked(self) -> bool:
        if not self.stop_on_obstacle:
            return False
        left_blocked = (0.02 < self.us_left_dist < self.us_stop_dist)
        right_blocked = (0.02 < self.us_right_dist < self.us_stop_dist)
        return self.obstacle_flag or left_blocked or right_blocked

    def line_error_callback(self, msg: Vector3):
        self.line_visible = (msg.z > 0.5)
        if self.line_visible:
            self.current_error = float(msg.x)
            self.last_valid_error = self.current_error
            self.last_line_seen_time = self.get_clock().now()

    def obstacle_callback(self, msg: Bool):
        self.obstacle_flag = bool(msg.data)

    def hw_status_callback(self, msg: String):
        """Sincroniza FSM exclusivamente com a segurança física do ESP32 (NR-12)."""
        try:
            data = json.loads(msg.data)
            safety = str(data.get('safety_state', 'UNKNOWN')).upper()
        except Exception:
            return

        self.hw_safety_state = safety

        if safety in ('HARDWARE_ESTOP_ACTIVE', 'WATCHDOG_TIMEOUT', 'DRIVER_FAULT'):
            if self.state != 'HARDWARE_ESTOP_ACTIVE':
                self.get_logger().warn(f'Emergência de hardware ESP32 ({safety})! Cortando movimento.')
            self.active = False
            self.current_cmd_speed = 0.0
            self.state = 'HARDWARE_ESTOP_ACTIVE'
        elif safety == 'ESTOP_CLEARED_PENDING_RESET':
            self.active = False
            self.current_cmd_speed = 0.0
            self.state = 'RECOVERY_PENDING'
        elif safety == 'OK':
            if self.state in ('HARDWARE_ESTOP_ACTIVE', 'RECOVERY_PENDING'):
                self.state = 'IDLE'
                self.get_logger().info('Rearme confirmado pelo ESP32! AGV em estado IDLE.')

    def command_callback(self, msg: String):
        cmd = msg.data.strip().upper()
        if cmd in ('START', 'GO', 'RUN'):
            self._request_start()
        elif cmd in ('STOP', 'IDLE', 'PAUSE'):
            self._request_stop()
        elif cmd in ('RESET', 'REARM'):
            self._request_reset()

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
        if self.hw_safety_state in ('HARDWARE_ESTOP_ACTIVE', 'ESTOP_CLEARED_PENDING_RESET', 'WATCHDOG_TIMEOUT', 'DRIVER_FAULT'):
            self.get_logger().warn(f'Comando START recusado: segurança hardware={self.hw_safety_state} (execute rearme!).')
            return
        if self._is_ultrasonic_blocked():
            self.get_logger().warn('Comando START recusado: obstáculo frontal nos sensores ultrassônicos!')
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

    def _request_reset(self):
        if self.hw_safety_state in ('HARDWARE_ESTOP_ACTIVE', 'ESTOP_CLEARED_PENDING_RESET', 'WATCHDOG_TIMEOUT', 'DRIVER_FAULT'):
            self.get_logger().warn(f'Rearme local ignorado: aguardando /agv/reset_emergency do ESP32 (hw={self.hw_safety_state}).')
            return
        self.active = False
        self.current_cmd_speed = 0.0
        self.obstacle_flag = False
        self.state = 'IDLE'
        self.get_logger().info('>>> SISTEMA REARMADO PARA STANDBY (IDLE) <<<')

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

        # 0. Respeita intertravamento físico de hardware / recuperação NR-12
        if self.state in ('HARDWARE_ESTOP_ACTIVE', 'RECOVERY_PENDING') and self.hw_safety_state not in ('INIT', 'OK'):
            self._publish_zero()
            return

        # 1. Pausa por obstáculo nos 2x Ultrassônicos Frontais (apenas quando ativo ou muito próximo)
        if self.active and self._is_ultrasonic_blocked():
            self._publish_zero()
            self.emergency_pub.publish(Twist())
            self.state = 'STOP_CONFIRMED'
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

        self.state = 'EM_MOVIMENTO'

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
            err = self.current_error
            deriv = (err - self.prev_error) / dt
            self.prev_error = err

            w_cmd = -(kp * err + kd * deriv)
            w_cmd = max(-max_ang, min(max_ang, w_cmd))

            err_abs = min(1.0, abs(err))
            v_cmd = max(min_speed, base_speed * (1.0 - err_abs * slowdown))

            twist.linear.x = v_cmd
            twist.angular.z = w_cmd
            self.current_cmd_speed = v_cmd
        else:
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
