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
import struct
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from sensor_msgs.msg import Range
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool


MOTION_PROFILES = {
    'SUAVE_CARGA': {
        'base_linear_speed': 0.20,
        'min_linear_speed': 0.10,
        'max_angular_speed': 1.60,
        'max_linear_accel': 0.25,
        'max_linear_decel': 0.45,
        'max_linear_jerk': 0.80,
        'max_angular_accel': 2.50,
        'curve_type': 's_curve',
    },
    'PADRAO': {
        'base_linear_speed': 0.35,
        'min_linear_speed': 0.15,
        'max_angular_speed': 2.80,
        'max_linear_accel': 0.50,
        'max_linear_decel': 0.80,
        'max_linear_jerk': 2.00,
        'max_angular_accel': 5.00,
        'curve_type': 's_curve',
    },
    'TURBO': {
        'base_linear_speed': 0.55,
        'min_linear_speed': 0.22,
        'max_angular_speed': 3.80,
        'max_linear_accel': 1.00,
        'max_linear_decel': 1.40,
        'max_linear_jerk': 5.00,
        'max_angular_accel': 8.00,
        'curve_type': 'trapezoidal',
    },
    'PRECISAO': {
        'base_linear_speed': 0.14,
        'min_linear_speed': 0.08,
        'max_angular_speed': 1.40,
        'max_linear_accel': 0.18,
        'max_linear_decel': 0.40,
        'max_linear_jerk': 0.60,
        'max_angular_accel': 2.00,
        'curve_type': 's_curve',
    },
}


class LineFollowerNode(Node):
    def __init__(self):
        super().__init__('line_follower')

        # Parâmetros dinâmicos
        self.declare_parameter('auto_start', False)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel_line')
        self.declare_parameter('base_linear_speed', 0.35)
        self.declare_parameter('min_linear_speed', 0.15)
        self.declare_parameter('max_angular_speed', 2.80)
        self.declare_parameter('curve_slowdown_factor', 0.50)
        self.declare_parameter('kp', 3.20)
        self.declare_parameter('ki', 0.00)
        self.declare_parameter('kd', 0.25)
        self.declare_parameter('search_on_lost_line', True)
        self.declare_parameter('search_linear_speed', 0.12)
        self.declare_parameter('search_angular_speed', 1.20)
        self.declare_parameter('max_lost_line_time_sec', 4.0)
        self.declare_parameter('stop_on_obstacle', True)
        self.declare_parameter('ultrasonic_stop_distance_m', 0.25)

        # Parâmetros da Curva de Aceleração e Perfis de Movimento
        self.declare_parameter('motion_profile', 'PADRAO')
        self.declare_parameter('accel_curve_type', 's_curve')
        self.declare_parameter('max_linear_accel', 0.50)
        self.declare_parameter('max_linear_decel', 0.80)
        self.declare_parameter('max_linear_jerk', 2.00)
        self.declare_parameter('max_angular_accel', 5.00)

        self.active: bool = bool(self.get_parameter('auto_start').value)
        cmd_vel_topic: str = self.get_parameter('cmd_vel_topic').value
        self.stop_on_obstacle: bool = bool(self.get_parameter('stop_on_obstacle').value)
        self.us_stop_dist: float = float(self.get_parameter('ultrasonic_stop_distance_m').value)

        # Configuração ativa do Perfil e Curva de Aceleração
        self.active_profile: str = str(self.get_parameter('motion_profile').value).upper()
        self.curve_type: str = str(self.get_parameter('accel_curve_type').value).lower()
        if self.curve_type not in ('s_curve', 'trapezoidal', 'direto'):
            self.curve_type = 's_curve'
        self.base_speed: float = float(self.get_parameter('base_linear_speed').value)
        self.min_speed: float = float(self.get_parameter('min_linear_speed').value)
        self.max_ang_speed: float = float(self.get_parameter('max_angular_speed').value)
        self.max_accel: float = max(0.02, float(self.get_parameter('max_linear_accel').value))
        self.max_decel: float = max(0.02, float(self.get_parameter('max_linear_decel').value))
        self.max_jerk: float = max(0.05, float(self.get_parameter('max_linear_jerk').value))
        self.max_ang_accel: float = max(0.1, float(self.get_parameter('max_angular_accel').value))

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
        self.current_cmd_ang = 0.0
        self.current_accel = 0.0
        self.current_jerk = 0.0
        self.last_target_v = 0.0
        self.last_target_w = 0.0

        now = self.get_clock().now()
        self.last_control_time = now
        self.last_line_seen_time = now

        # Publishers
        self.cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
        self.emergency_pub = self.create_publisher(Twist, '/cmd_vel_emergency', 10)
        self.state_pub = self.create_publisher(String, '/agv/state', 10)
        self.profile_status_pub = self.create_publisher(String, '/agv/motion_profile_status', 10)

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
            Range, '/agv/ultrasonic_left', self.us_left_callback, 10, raw=True
        )
        self.us_right_sub = self.create_subscription(
            Range, '/agv/ultrasonic_right', self.us_right_callback, 10, raw=True
        )
        self.hw_status_sub = self.create_subscription(
            String, '/agv/hardware_status', self.hw_status_callback, 10
        )
        self.profile_cmd_sub = self.create_subscription(
            String, '/agv/motion_profile_command', self.motion_profile_callback, 10
        )

        # Service
        self.srv = self.create_service(
            SetBool, '/agv/set_following', self.set_following_callback
        )

        # Loop de controle a 30 Hz
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)

        self.get_logger().info(
            f'LineFollowerNode iniciado | Estado: {self.state} | '
            f'Perfil={self.active_profile} ({self.curve_type}) | '
            f'Ultrassônicos 2x HC-SR04 (corte={self.us_stop_dist:.2f}m, ativo={self.stop_on_obstacle})'
        )

    @staticmethod
    def _parse_raw_range(raw_msg) -> float:
        try:
            if isinstance(raw_msg, (bytes, bytearray, memoryview)):
                if len(raw_msg) < 16:
                    return float('inf')
                _, min_r, max_r, r = struct.unpack('<4f', bytes(raw_msg[-16:]))
            else:
                r = float(raw_msg.range)
                min_r = float(raw_msg.min_range)
                max_r = float(raw_msg.max_range)
            if math.isnan(r) or math.isinf(r) or r < min_r or r > max_r:
                return float('inf')
            return r
        except Exception:
            return float('inf')

    def us_left_callback(self, msg):
        self.us_left_dist = self._parse_raw_range(msg)

    def us_right_callback(self, msg):
        self.us_right_dist = self._parse_raw_range(msg)

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
            self.current_cmd_ang = 0.0
            self.current_accel = 0.0
            self.current_jerk = 0.0
            self.state = 'HARDWARE_ESTOP_ACTIVE'
        elif safety == 'ESTOP_CLEARED_PENDING_RESET':
            self.active = False
            self.current_cmd_speed = 0.0
            self.current_cmd_ang = 0.0
            self.current_accel = 0.0
            self.current_jerk = 0.0
            self.state = 'RECOVERY_PENDING'
        elif safety == 'OK':
            if self.state in ('HARDWARE_ESTOP_ACTIVE', 'RECOVERY_PENDING'):
                self.state = 'IDLE'
                self.get_logger().info('Rearme confirmado pelo ESP32! AGV em estado IDLE.')

    def motion_profile_callback(self, msg: String):
        """Atualiza perfil de movimento e parâmetros da curva de aceleração em tempo real."""
        try:
            data = json.loads(msg.data)
            if not isinstance(data, dict):
                return
        except Exception as exc:
            self.get_logger().warn(f'Comando inválido em /agv/motion_profile_command: {exc}')
            return

        if 'profile' in data:
            prof = str(data['profile']).upper()
            if prof in MOTION_PROFILES:
                cfg = MOTION_PROFILES[prof]
                self.active_profile = prof
                self.base_speed = cfg['base_linear_speed']
                self.min_speed = cfg['min_linear_speed']
                self.max_ang_speed = cfg['max_angular_speed']
                self.max_accel = cfg['max_linear_accel']
                self.max_decel = cfg['max_linear_decel']
                self.max_jerk = cfg['max_linear_jerk']
                self.max_ang_accel = cfg['max_angular_accel']
                self.curve_type = cfg['curve_type']
            elif prof == 'PERSONALIZADO':
                self.active_profile = 'PERSONALIZADO'

        custom_edited = False
        if 'curve_type' in data:
            ct = str(data['curve_type']).lower()
            if ct in ('s_curve', 'trapezoidal', 'direto') and ct != self.curve_type:
                self.curve_type = ct
                custom_edited = True
        if 'base_speed' in data:
            self.base_speed = max(0.05, min(0.80, float(data['base_speed'])))
            custom_edited = True
        if 'min_speed' in data:
            self.min_speed = max(0.04, min(self.base_speed, float(data['min_speed'])))
            custom_edited = True
        if 'max_angular_speed' in data:
            self.max_ang_speed = max(0.5, min(5.0, float(data['max_angular_speed'])))
            custom_edited = True
        if 'max_accel' in data:
            self.max_accel = max(0.05, min(3.0, float(data['max_accel'])))
            custom_edited = True
        if 'max_decel' in data:
            self.max_decel = max(0.05, min(4.0, float(data['max_decel'])))
            custom_edited = True
        if 'max_jerk' in data:
            self.max_jerk = max(0.10, min(15.0, float(data['max_jerk'])))
            custom_edited = True
        if 'max_angular_accel' in data:
            self.max_ang_accel = max(0.5, min(15.0, float(data['max_angular_accel'])))
            custom_edited = True

        if custom_edited and 'profile' not in data:
            self.active_profile = 'PERSONALIZADO'

        self.get_logger().info(
            f"[PERFIL MOVIMENTO] {self.active_profile} | curva={self.curve_type} | "
            f"v={self.base_speed:.2f} m/s | a={self.max_accel:.2f} m/s² | "
            f"d={self.max_decel:.2f} m/s² | J={self.max_jerk:.2f} m/s³"
        )
        self._publish_motion_profile_status()

    def _apply_motion_profile_step(self, target_v: float, target_w: float, dt: float):
        """Aplica curva S (jerk limitado), trapezoidal ou passo direto sobre (target_v, target_w)."""
        self.last_target_v = float(target_v)
        self.last_target_w = float(target_w)

        v_cur = self.current_cmd_speed
        a_cur = self.current_accel
        dv = target_v - v_cur

        if self.curve_type == 'direto':
            v_next = target_v
            a_next = (v_next - v_cur) / dt
            jerk_now = (a_next - a_cur) / dt
            w_next = target_w
        elif self.curve_type == 'trapezoidal':
            max_step = (self.max_accel if dv >= 0.0 else self.max_decel) * dt
            if abs(dv) <= max_step:
                v_next = target_v
            else:
                v_next = v_cur + (max_step if dv >= 0.0 else -max_step)
            a_next = (v_next - v_cur) / dt
            jerk_now = (a_next - a_cur) / dt

            dw = target_w - self.current_cmd_ang
            w_step = self.max_ang_accel * dt
            if abs(dw) <= w_step:
                w_next = target_w
            else:
                w_next = self.current_cmd_ang + (w_step if dw >= 0.0 else -w_step)
        else:
            # S-Curve com limitação de Jerk (m/s^3) e desaceleração antecipada sem overshoot
            j_max = self.max_jerk
            if abs(dv) < 1e-4 and abs(a_cur) <= j_max * dt * 1.1:
                v_next = target_v
                a_next = 0.0
                jerk_now = (0.0 - a_cur) / dt
            else:
                if dv >= 0.0:
                    a_des = min(self.max_accel, math.sqrt(2.0 * j_max * dv))
                else:
                    a_des = max(-self.max_decel, -math.sqrt(2.0 * j_max * (-dv)))
                da_max = j_max * dt
                a_next = a_cur + max(-da_max, min(da_max, a_des - a_cur))
                jerk_now = (a_next - a_cur) / dt
                v_cand = v_cur + 0.5 * (a_cur + a_next) * dt
                if (dv >= 0.0 and v_cand >= target_v) or (dv < 0.0 and v_cand <= target_v):
                    v_next = target_v
                    a_next = 0.0
                else:
                    v_next = v_cand

            dw = target_w - self.current_cmd_ang
            w_step = self.max_ang_accel * dt
            if abs(dw) <= w_step:
                w_next = target_w
            else:
                w_next = self.current_cmd_ang + (w_step if dw >= 0.0 else -w_step)

        self.current_cmd_speed = v_next
        self.current_cmd_ang = w_next
        self.current_accel = a_next
        self.current_jerk = jerk_now
        return v_next, w_next

    def _publish_motion_profile_status(self):
        msg = String()
        msg.data = json.dumps({
            'profile': self.active_profile,
            'curve_type': self.curve_type,
            'base_speed': round(self.base_speed, 3),
            'min_speed': round(self.min_speed, 3),
            'max_angular_speed': round(self.max_ang_speed, 3),
            'max_accel': round(self.max_accel, 3),
            'max_decel': round(self.max_decel, 3),
            'max_jerk': round(self.max_jerk, 3),
            'max_angular_accel': round(self.max_ang_accel, 3),
            'target_v': round(self.last_target_v, 3),
            'profiled_v': round(self.current_cmd_speed, 3),
            'current_accel': round(self.current_accel, 3),
            'current_jerk': round(self.current_jerk, 3),
            'target_w': round(self.last_target_w, 3),
            'profiled_w': round(self.current_cmd_ang, 3),
        })
        self.profile_status_pub.publish(msg)

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
        self.current_cmd_ang = 0.0
        self.current_accel = 0.0
        self.current_jerk = 0.0
        self.last_target_v = 0.0
        self.last_target_w = 0.0
        self.obstacle_flag = False
        self.state = 'IDLE'
        self.get_logger().info('>>> SISTEMA REARMADO PARA STANDBY (IDLE) <<<')

    def _publish_zero(self):
        t = Twist()
        self.cmd_pub.publish(t)
        self.current_cmd_speed = 0.0
        self.current_cmd_ang = 0.0
        self.current_accel = 0.0
        self.current_jerk = 0.0
        self.last_target_v = 0.0
        self.last_target_w = 0.0

    def control_loop(self):
        try:
            self._control_step()
        finally:
            self._publish_motion_profile_status()

    def _control_step(self):
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

        # 2. Trata Parada Solicitada (Rampa/Curva S de Desaceleração)
        if self.state == 'REMOTE_STOP_REQUESTED':
            if abs(self.current_cmd_speed) > 0.015 or abs(self.current_accel) > 0.05:
                v_out, w_out = self._apply_motion_profile_step(0.0, 0.0, dt)
                t = Twist()
                t.linear.x = max(0.0, v_out)
                t.angular.z = w_out
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
        base_speed = self.base_speed
        min_speed = self.min_speed
        max_ang = self.max_ang_speed
        slowdown = float(self.get_parameter('curve_slowdown_factor').value)
        kp = float(self.get_parameter('kp').value)
        kd = float(self.get_parameter('kd').value)

        if self.line_visible:
            err = self.current_error
            deriv = (err - self.prev_error) / dt
            self.prev_error = err

            w_target = -(kp * err + kd * deriv)
            w_target = max(-max_ang, min(max_ang, w_target))

            err_abs = min(1.0, abs(err))
            v_target = max(min_speed, base_speed * (1.0 - err_abs * slowdown))

            v_out, w_out = self._apply_motion_profile_step(v_target, w_target, dt)
            twist.linear.x = v_out
            twist.angular.z = w_out
        else:
            if time_lost > max_lost_time:
                self._publish_zero()
                self.state = 'LOST_LINE_STOPPED'
                return
            v_target = float(self.get_parameter('search_linear_speed').value)
            turn_dir = 1.0 if self.last_valid_error < 0.0 else -1.0
            w_target = turn_dir * float(self.get_parameter('search_angular_speed').value)
            v_out, w_out = self._apply_motion_profile_step(v_target, w_target, dt)
            twist.linear.x = v_out
            twist.angular.z = w_out

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
