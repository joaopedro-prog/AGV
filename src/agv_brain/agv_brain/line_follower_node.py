#!/usr/bin/env python3
"""
Nó Controlador PID Seguidor de Linha + Máquina de Estados do AGV.

Orquestração ("Seguir linha quando eu mandar"):
  - Inicia no estado IDLE (Parado) por padrão (a menos que auto_start=True).
  - Pode ser ativado/desativado a qualquer momento por:
      1) Serviço ROS 2:
         ros2 service call /agv/set_following std_srvs/srv/SetBool "{data: true}"
      2) Tópico ROS 2:
         ros2 topic pub --once /agv/command std_msgs/msg/String "{data: 'START'}"
      3) Painel de comando rápido:
         ros2 run agv_brain agv_cmd start
         ros2 run agv_brain agv_cmd stop
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool


class LineFollowerNode(Node):
    def __init__(self):
        super().__init__('line_follower')

        # Parâmetros do brain_params.yaml
        self.declare_parameter('auto_start', False)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel_line')
        self.declare_parameter('base_linear_speed', 0.22)
        self.declare_parameter('min_linear_speed', 0.08)
        self.declare_parameter('max_angular_speed', 1.50)
        self.declare_parameter('curve_slowdown_factor', 0.65)
        self.declare_parameter('kp', 1.25)
        self.declare_parameter('ki', 0.00)
        self.declare_parameter('kd', 0.25)
        self.declare_parameter('search_on_lost_line', True)
        self.declare_parameter('search_angular_speed', 0.45)
        self.declare_parameter('max_lost_line_time_sec', 3.0)
        self.declare_parameter('stop_on_obstacle', True)

        self.active: bool = bool(self.get_parameter('auto_start').value)
        cmd_vel_topic: str = self.get_parameter('cmd_vel_topic').value

        # Estado do PID e sensores
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

        # Service para ligar/desligar seguidor de linha
        self.srv = self.create_service(
            SetBool, '/agv/set_following', self.set_following_callback
        )

        # Loop de controle a 30 Hz
        self.timer = self.create_timer(1.0 / 30.0, self.control_loop)

        initial_state = 'FOLLOWING (ATIVO)' if self.active else 'IDLE (AGUARDANDO COMANDO START)'
        self.get_logger().info(
            f'LineFollowerNode iniciado | Estado inicial: {initial_state} | '
            f'Publicando em: {cmd_vel_topic}'
        )

    def line_error_callback(self, msg: Vector3):
        """Recebe erro normalizado do detector de visão."""
        self.line_visible = (msg.z > 0.5)
        if self.line_visible:
            self.current_error = float(msg.x)
            self.last_valid_error = self.current_error
            self.last_line_seen_time = self.get_clock().now()

    def obstacle_callback(self, msg: Bool):
        """Recebe alerta de obstáculo dos sensores."""
        self.obstacle_detected = bool(msg.data)

    def command_callback(self, msg: String):
        """Recebe comandos textuais em /agv/command ('START', 'STOP', 'TOGGLE')."""
        cmd = msg.data.strip().upper()
        if cmd in ('START', 'GO', 'RUN', 'ON', '1'):
            self._set_active(True)
        elif cmd in ('STOP', 'IDLE', 'PAUSE', 'OFF', '0'):
            self._set_active(False)
        elif cmd == 'TOGGLE':
            self._set_active(not self.active)

    def set_following_callback(self, request: SetBool.Request, response: SetBool.Response):
        """Serviço /agv/set_following para ativar ou parar o AGV."""
        self._set_active(request.data)
        response.success = True
        response.message = (
            'AGV iniciou o seguidor de linha!' if self.active else 'AGV parado (IDLE).'
        )
        return response

    def _set_active(self, enable: bool):
        """Altera estado da máquina de estados com reset seguro do PID."""
        self.active = enable
        self.integral_error = 0.0
        self.prev_error = 0.0
        self.last_line_seen_time = self.get_clock().now()
        if not enable:
            self._publish_zero_velocity()
            self.get_logger().info('>>> AGV PARADO (Estado: IDLE) <<<')
        else:
            self.get_logger().info('>>> AGV ATIVADO (Estado: FOLLOWING LINE) <<<')

    def _publish_zero_velocity(self):
        twist = Twist()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.cmd_pub.publish(twist)

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_control_time).nanoseconds / 1e9
        self.last_control_time = now
        if dt <= 0.0 or dt > 1.0:
            dt = 1.0 / 30.0

        # 1. Se está em IDLE, mantém parado e não envia comandos caso o usuário use joystick
        if not self.active:
            state_msg = String()
            state_msg.data = 'IDLE'
            self.state_pub.publish(state_msg)
            return

        # 2. Verifica parada de segurança por obstáculo
        stop_on_obs = bool(self.get_parameter('stop_on_obstacle').value)
        if stop_on_obs and self.obstacle_detected:
            self._publish_zero_velocity()
            state_msg = String()
            state_msg.data = 'PAUSED_OBSTACLE'
            self.state_pub.publish(state_msg)
            return

        # Leitura dinâmica dos parâmetros PID
        base_speed = float(self.get_parameter('base_linear_speed').value)
        min_speed = float(self.get_parameter('min_linear_speed').value)
        max_ang = float(self.get_parameter('max_angular_speed').value)
        slowdown = float(self.get_parameter('curve_slowdown_factor').value)
        kp = float(self.get_parameter('kp').value)
        ki = float(self.get_parameter('ki').value)
        kd = float(self.get_parameter('kd').value)
        search_enabled = bool(self.get_parameter('search_on_lost_line').value)
        search_ang = float(self.get_parameter('search_angular_speed').value)
        max_lost_time = float(self.get_parameter('max_lost_line_time_sec').value)

        twist = Twist()
        state_str = 'FOLLOWING'

        # 3. Linha visível -> Controle PID normal
        if self.line_visible:
            error = self.current_error
            self.integral_error += error * dt
            # Anti-windup
            self.integral_error = max(-1.0, min(1.0, self.integral_error))
            derivative = (error - self.prev_error) / dt
            self.prev_error = error

            # Erro positivo significa que a linha está à direita do centro da imagem -> girar para a direita (angular.z negativo)
            ang_z = -(kp * error + ki * self.integral_error + kd * derivative)
            ang_z = max(-max_ang, min(max_ang, ang_z))

            # Reduz a velocidade linear suavemente quanto maior for o erro (curvas)
            speed_factor = max(0.0, 1.0 - slowdown * abs(error))
            lin_x = max(min_speed, base_speed * speed_factor)

            twist.linear.x = float(lin_x)
            twist.angular.z = float(ang_z)

        # 4. Linha perdida -> Busca ou parada de segurança
        else:
            time_since_seen = (now - self.last_line_seen_time).nanoseconds / 1e9
            if search_enabled and time_since_seen < max_lost_time:
                state_str = 'SEARCHING_LINE'
                twist.linear.x = 0.0
                # Gira para o lado onde a linha foi vista pela última vez
                direction = -1.0 if self.last_valid_error >= 0.0 else 1.0
                twist.angular.z = float(direction * search_ang)
            else:
                state_str = 'LOST_LINE_STOPPED'
                twist.linear.x = 0.0
                twist.angular.z = 0.0

        self.cmd_pub.publish(twist)

        state_msg = String()
        state_msg.data = state_str
        self.state_pub.publish(state_msg)


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
