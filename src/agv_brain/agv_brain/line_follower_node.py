#!/usr/bin/env python3
"""
Nó Controlador PID Seguidor de Linha + Máquina de Estados do AGV.

Comportamento:
1. Inicia em IDLE (Parado) para segurança.
2. Ativado via:
   - ros2 run agv_brain agv_cmd start
   - ros2 service call /agv/set_following std_srvs/srv/SetBool "{data: true}"
3. Quando a linha está visível:
   - Executa controle PID sobre o erro normalizado.
   - Reduz a velocidade linear proporcionalmente ao módulo do erro para contornar curvas com precisão.
4. Quando a linha sai momentaneamente do campo de visão (curva fechada):
   - Entra em SEARCHING_LINE com avanço suave e rotação em direção ao último lado visto.
   - Se não reencontrar a linha dentro do tempo limite (ex: 4s), para totalmente em LOST_LINE_STOPPED.
5. Se detectar obstáculo à frente (/agv/obstacle_detected):
   - Pausa imediatamente o movimento até que o obstáculo seja removido.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool


class LineFollowerNode(Node):
    def __init__(self):
        super().__init__('line_follower')

        # Parâmetros dinâmicos do brain_params.yaml
        self.declare_parameter('auto_start', False)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel_line')
        self.declare_parameter('base_linear_speed', 0.20)
        self.declare_parameter('min_linear_speed', 0.08)
        self.declare_parameter('max_angular_speed', 1.50)
        self.declare_parameter('curve_slowdown_factor', 0.70)
        self.declare_parameter('kp', 1.40)
        self.declare_parameter('ki', 0.00)
        self.declare_parameter('kd', 0.30)
        self.declare_parameter('search_on_lost_line', True)
        self.declare_parameter('search_linear_speed', 0.04)
        self.declare_parameter('search_angular_speed', 0.55)
        self.declare_parameter('max_lost_line_time_sec', 4.0)
        self.declare_parameter('stop_on_obstacle', True)

        self.active: bool = bool(self.get_parameter('auto_start').value)
        cmd_vel_topic: str = self.get_parameter('cmd_vel_topic').value

        # Estado interno do seguidor
        self.line_visible = False
        self.current_error = 0.0
        self.last_valid_error = 0.0
        self.prev_error = 0.0
        self.integral_error = 0.0
        self.obstacle_detected = False

        now = self.get_clock().now()
        self.last_control_time = now
        self.last_line_seen_time = now

        # Publishers
        self.cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
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

        # Service para controle remoto
        self.srv = self.create_service(
            SetBool, '/agv/set_following', self.set_following_callback
        )

        # Loop de controle a 30 Hz
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)

        status_init = 'ATIVO' if self.active else 'IDLE (AGUARDANDO START)'
        self.get_logger().info(
            f'LineFollowerNode iniciado | Estado: {status_init} | Saída: {cmd_vel_topic}'
        )

    def line_error_callback(self, msg: Vector3):
        """Recebe o erro de desvio lateral da visão."""
        self.line_visible = (msg.z > 0.5)
        if self.line_visible:
            self.current_error = float(msg.x)
            self.last_valid_error = self.current_error
            self.last_line_seen_time = self.get_clock().now()

    def obstacle_callback(self, msg: Bool):
        self.obstacle_detected = bool(msg.data)

    def command_callback(self, msg: String):
        cmd = msg.data.strip().upper()
        if cmd in ('START', 'GO', 'RUN', 'ON', '1'):
            self._set_active(True)
        elif cmd in ('STOP', 'IDLE', 'PAUSE', 'OFF', '0'):
            self._set_active(False)
        elif cmd == 'TOGGLE':
            self._set_active(not self.active)

    def set_following_callback(self, request: SetBool.Request, response: SetBool.Response):
        self._set_active(request.data)
        response.success = True
        response.message = 'AGV em movimento (Seguindo linha)' if self.active else 'AGV parado (IDLE).'
        return response

    def _set_active(self, enable: bool):
        self.active = enable
        self.integral_error = 0.0
        self.prev_error = 0.0
        self.last_line_seen_time = self.get_clock().now()
        if not enable:
            self._publish_zero_velocity()
            self.get_logger().info('>>> AGV PARADO (Estado: IDLE) <<<')
        else:
            self.get_logger().info('>>> AGV ATIVADO (Estado: FOLLOWING) <<<')

    def _publish_zero_velocity(self):
        t = Twist()
        t.linear.x = 0.0
        t.angular.z = 0.0
        self.cmd_pub.publish(t)

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_control_time).nanoseconds / 1e9
        self.last_control_time = now
        if dt <= 0.0 or dt > 0.5:
            dt = 1.0 / 30.0

        # 1. Se está inativo, publica IDLE e não envia comandos aos motores
        if not self.active:
            s_msg = String()
            s_msg.data = 'IDLE'
            self.state_pub.publish(s_msg)
            return

        # 2. Parada por obstáculo
        if bool(self.get_parameter('stop_on_obstacle').value) and self.obstacle_detected:
            self._publish_zero_velocity()
            s_msg = String()
            s_msg.data = 'PAUSED_OBSTACLE'
            self.state_pub.publish(s_msg)
            return

        # Parâmetros
        base_speed = float(self.get_parameter('base_linear_speed').value)
        min_speed = float(self.get_parameter('min_linear_speed').value)
        max_ang = float(self.get_parameter('max_angular_speed').value)
        slowdown = float(self.get_parameter('curve_slowdown_factor').value)
        kp = float(self.get_parameter('kp').value)
        ki = float(self.get_parameter('ki').value)
        kd = float(self.get_parameter('kd').value)
        search_enabled = bool(self.get_parameter('search_on_lost_line').value)
        search_lin = float(self.get_parameter('search_linear_speed').value)
        search_ang = float(self.get_parameter('search_angular_speed').value)
        max_lost_time = float(self.get_parameter('max_lost_line_time_sec').value)

        twist = Twist()
        state_str = 'FOLLOWING'

        # 3. Linha visível: Controle PID em ação
        if self.line_visible:
            error = self.current_error
            self.integral_error += error * dt
            self.integral_error = max(-1.0, min(1.0, self.integral_error))  # Anti-windup
            derivative = (error - self.prev_error) / dt
            self.prev_error = error

            # Erro positivo (linha à direita do centro) -> angular.z negativo (vira à direita)
            ang_z = -(kp * error + ki * self.integral_error + kd * derivative)
            ang_z = max(-max_ang, min(max_ang, ang_z))

            # Reduz a velocidade linear conforme o erro lateral cresce (curvas suaves e precisas)
            speed_factor = max(0.15, 1.0 - slowdown * abs(error))
            lin_x = max(min_speed, base_speed * speed_factor)

            twist.linear.x = float(lin_x)
            twist.angular.z = float(ang_z)

        # 4. Linha momentaneamente perdida (curva acentuada)
        else:
            time_since_seen = (now - self.last_line_seen_time).nanoseconds / 1e9
            if search_enabled and time_since_seen < max_lost_time:
                state_str = 'SEARCHING_LINE'
                twist.linear.x = float(search_lin)
                # Gira em direção ao último lado onde a linha foi avistada
                direction = -1.0 if self.last_valid_error >= 0.0 else 1.0
                twist.angular.z = float(direction * search_ang)
            else:
                state_str = 'LOST_LINE_STOPPED'
                twist.linear.x = 0.0
                twist.angular.z = 0.0

        self.cmd_pub.publish(twist)

        s_msg = String()
        s_msg.data = state_str
        self.state_pub.publish(s_msg)


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
