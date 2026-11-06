#!/usr/bin/env python3
"""
Nó do Dashboard Web e Servidor HMI do AGV.

Responsabilidades:
1. Coleta telemetria em tempo real:
   - /odom (Odometria e velocidade real)
   - /agv/state (Estado da FSM: IDLE, EM_MOVIMENTO, REMOTE_STOP_REQUESTED, STOP_CONFIRMED, HARDWARE_ESTOP_ACTIVE)
   - /agv/battery_voltage (Tensão da bateria)
   - /agv/line_error (Erro da linha)
   - /agv/hardware_status (Link serial e integridade)
   - /agv/obstacle_detected (Alerta de obstáculo)
2. Publica comandos do operador:
   - /agv/command: START / STOP
   - /cmd_vel_emergency: Parada imediata prioridade 255
   - /cmd_vel_joy: Teleoperação manual prioridade 100
   - Chama serviço /agv/reset_emergency para procedimento de rearme
3. Serve a interface web moderna em http://0.0.0.0:8080 com suporte a API REST e WebSocket.
"""

import http.server
import json
import os
import socketserver
import threading
from typing import Dict, Any

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, Float32, String
from std_srvs.srv import Trigger


class DashboardNode(Node):
    def __init__(self):
        super().__init__('agv_dashboard_node')

        self.declare_parameter('web_port', 8080)
        self.port: int = int(self.get_parameter('web_port').value)

        # Estado interno de telemetria
        self.telemetry: Dict[str, Any] = {
            'state': 'IDLE',
            'battery_v': 12.0,
            'obstacle': False,
            'line_error': 0.0,
            'line_visible': False,
            'odom_x': 0.0,
            'odom_y': 0.0,
            'speed_lin': 0.0,
            'speed_ang': 0.0,
            'serial_connected': False,
            'odometry_valid': False,
            'safety_state': 'INIT',
            'crc_errors': 0
        }

        # Subscribers
        self.sub_state = self.create_subscription(
            String, '/agv/state', self._state_cb, 10
        )
        self.sub_bat = self.create_subscription(
            Float32, '/agv/battery_voltage', self._bat_cb, 10
        )
        self.sub_obs = self.create_subscription(
            Bool, '/agv/obstacle_detected', self._obs_cb, 10
        )
        self.sub_error = self.create_subscription(
            Vector3, '/agv/line_error', self._error_cb, 10
        )
        self.sub_odom = self.create_subscription(
            Odometry, '/odom', self._odom_cb, 10
        )
        self.sub_hw = self.create_subscription(
            String, '/agv/hardware_status', self._hw_cb, 10
        )

        # Publishers
        self.pub_cmd = self.create_publisher(String, '/agv/command', 10)
        self.pub_emergency = self.create_publisher(Twist, '/cmd_vel_emergency', 10)
        self.pub_teleop = self.create_publisher(Twist, '/cmd_vel_joy', 10)

        # Service Client de Rearme
        self.cli_reset = self.create_client(Trigger, '/agv/reset_emergency')

        # Inicia Servidor HTTP em thread separada
        self._start_http_server()

        self.get_logger().info(f'Dashboard Web AGV iniciado na porta {self.port}!')

    def _state_cb(self, msg: String):
        self.telemetry['state'] = msg.data

    def _bat_cb(self, msg: Float32):
        self.telemetry['battery_v'] = round(msg.data, 2)

    def _obs_cb(self, msg: Bool):
        self.telemetry['obstacle'] = msg.data

    def _error_cb(self, msg: Vector3):
        self.telemetry['line_error'] = round(msg.x, 2)
        self.telemetry['line_visible'] = (msg.z > 0.5)

    def _odom_cb(self, msg: Odometry):
        self.telemetry['odom_x'] = round(msg.pose.pose.position.x, 2)
        self.telemetry['odom_y'] = round(msg.pose.pose.position.y, 2)
        self.telemetry['speed_lin'] = round(msg.twist.twist.linear.x, 2)
        self.telemetry['speed_ang'] = round(msg.twist.twist.angular.z, 2)

    def _hw_cb(self, msg: String):
        try:
            data = json.loads(msg.data)
            self.telemetry['serial_connected'] = data.get('serial_connected', False)
            self.telemetry['odometry_valid'] = data.get('odometry_valid', False)
            self.telemetry['safety_state'] = data.get('safety_state', 'UNKNOWN')
            self.telemetry['crc_errors'] = data.get('crc_errors', 0)
        except Exception:
            pass

    def handle_user_command(self, action: str, params: dict) -> dict:
        action = action.lower()
        if action == 'start':
            msg = String()
            msg.data = 'START'
            self.pub_cmd.publish(msg)
            return {'status': 'ok', 'message': 'START publicado'}

        elif action == 'stop':
            msg = String()
            msg.data = 'STOP'
            self.pub_cmd.publish(msg)
            return {'status': 'ok', 'message': 'STOP publicado'}

        elif action == 'emergency':
            t = Twist()
            self.pub_emergency.publish(t)
            # Envia também comando de parada
            s = String()
            s.data = 'STOP'
            self.pub_cmd.publish(s)
            return {'status': 'ok', 'message': 'EMERGÊNCIA 255 acionada'}

        elif action == 'reset':
            if self.cli_reset.wait_for_service(timeout_sec=1.0):
                req = Trigger.Request()
                future = self.cli_reset.call_async(req)
                return {'status': 'ok', 'message': 'Solicitação de rearme transmitida'}
            return {'status': 'error', 'message': 'Serviço de rearme não disponível'}

        elif action == 'teleop':
            v = float(params.get('linear', 0.0))
            w = float(params.get('angular', 0.0))
            t = Twist()
            t.linear.x = v
            t.angular.z = w
            self.pub_teleop.publish(t)
            return {'status': 'ok', 'message': 'Comando teleop publicado'}

        return {'status': 'error', 'message': f'Ação desconhecida: {action}'}

    def _start_http_server(self):
        node_ref = self
        static_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'static'
        )

        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=static_dir, **kwargs)

            def do_GET(self):
                if self.path == '/api/status':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(node_ref.telemetry).encode('utf-8'))
                    return
                super().do_GET()

            def do_POST(self):
                if self.path == '/api/command':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode('utf-8')
                    try:
                        data = json.loads(body)
                        action = data.get('action', '')
                        res = node_ref.handle_user_command(action, data)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(res).encode('utf-8'))
                    except Exception as e:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(str(e).encode('utf-8'))
                    return
                self.send_response(404)
                self.end_headers()

            def log_message(self, format, *args):
                # Silencia logs de GET estático no terminal
                return

        def run_server():
            with socketserver.TCPServer(('0.0.0.0', self.port), CustomHandler) as httpd:
                httpd.serve_forever()

        t = threading.Thread(target=run_server, daemon=True)
        t.start()


def main(args=None):
    rclpy.init(args=args)
    node = DashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
