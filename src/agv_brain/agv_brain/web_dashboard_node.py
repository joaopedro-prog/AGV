#!/usr/bin/env python3
"""
Nó do Dashboard Web do AGV (ROS 2 Humble).
Servidor HTTP nativo em tempo real para controle, transmissão de vídeo e telemetria.

Recursos:
- Transmissão MJPEG ao vivo da câmera (/camera/image_raw e /agv/line_debug_image).
- Comandos START / STOP para o seguidor de linha autônomo (/agv/command e /agv/set_following).
- Teleoperação manual via teclado/toque (/cmd_vel_joy com prioridade 100).
- Telemetria de sensores (odometria, ultrassônico, linha, velocidades, bateria).
- Standalone e zero-dependências externas (utiliza rclpy, cv_bridge, opencv e stdlib Python).
"""

import os
import sys
import time
import math
import json
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from sensor_msgs.msg import Image, Range
from std_msgs.msg import Bool, String, Float32
from nav_msgs.msg import Odometry
from std_srvs.srv import SetBool

try:
    import cv2
    import numpy as np
    from cv_bridge import CvBridge
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    from ament_index_python.packages import get_package_share_directory
    HAS_AMENT = True
except ImportError:
    HAS_AMENT = False


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Converte quaternion (x, y, z, w) para ângulo Yaw em radianos."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class WebDashboardNode(Node):
    def __init__(self):
        super().__init__('web_dashboard')

        # Parâmetros
        self.declare_parameter('port', 5000)
        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('jpeg_quality', 75)
        self.declare_parameter('max_fps', 25)

        self.port = int(self.get_parameter('port').value)
        self.host = str(self.get_parameter('host').value)
        self.jpeg_quality = int(self.get_parameter('jpeg_quality').value)
        self.max_fps = int(self.get_parameter('max_fps').value)

        # Localização da pasta de arquivos estáticos da web
        self.web_dir = self._find_web_directory()

        # Ponte OpenCV
        self.bridge = CvBridge() if HAS_OPENCV else None

        # Bloqueios e estados compartilhados de vídeo
        self.frame_lock = threading.Lock()
        self.latest_raw_jpeg: bytes = b''
        self.latest_debug_jpeg: bytes = b''
        self.last_raw_time = 0.0
        self.last_debug_time = 0.0

        # Estado da telemetria
        self.telemetry_lock = threading.Lock()
        self.telemetry = {
            'state': 'IDLE',
            'line_error': 0.0,
            'line_error_px': 0.0,
            'line_found': False,
            'linear_velocity': 0.0,
            'angular_velocity': 0.0,
            'ultrasonic_distance': None,
            'obstacle_detected': False,
            'battery_voltage': 12.4,
            'odom_x': 0.0,
            'odom_y': 0.0,
            'odom_yaw': 0.0,
            'timestamp': time.time(),
        }

        # Publishers
        self.cmd_pub = self.create_publisher(String, '/agv/command', 10)
        self.teleop_pub = self.create_publisher(Twist, '/cmd_vel_joy', 10)

        # Service Client para set_following
        self.srv_client = self.create_client(SetBool, '/agv/set_following')

        # Subscribers
        self.sub_debug_img = self.create_subscription(
            Image, '/agv/line_debug_image', self._debug_image_callback, 10
        )
        self.sub_raw_img = self.create_subscription(
            Image, '/camera/image_raw', self._raw_image_callback, 10
        )
        self.sub_line_err = self.create_subscription(
            Vector3, '/agv/line_error', self._line_error_callback, 10
        )
        self.sub_state = self.create_subscription(
            String, '/agv/state', self._state_callback, 10
        )
        self.sub_obstacle = self.create_subscription(
            Bool, '/agv/obstacle_detected', self._obstacle_callback, 10
        )
        self.sub_ultrasonic = self.create_subscription(
            Range, '/agv/ultrasonic', self._ultrasonic_callback, 10
        )
        self.sub_odom = self.create_subscription(
            Odometry, '/odom', self._odom_callback, 10
        )
        self.sub_cmd_vel = self.create_subscription(
            Twist, '/cmd_vel', self._cmd_vel_callback, 10
        )
        self.sub_battery = self.create_subscription(
            Float32, '/agv/battery_voltage', self._battery_callback, 10
        )

        # Gera imagem standby inicial
        self._generate_standby_frames()

        # Inicia servidor HTTP em thread separada
        self.http_server = None
        self.server_thread = threading.Thread(target=self._run_http_server, daemon=True)
        self.server_thread.start()

        self.get_logger().info('====================================================')
        self.get_logger().info(f' AGV Web Dashboard rodando em: http://localhost:{self.port}')
        self.get_logger().info(f' Pasta de arquivos web: {self.web_dir}')
        self.get_logger().info('====================================================')

    def _find_web_directory(self) -> str:
        """Localiza a pasta com os arquivos index.html, style.css e app.js."""
        # 1. Checa pasta relativa ao arquivo atual
        local_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
        if os.path.isdir(local_dir):
            return local_dir

        # 2. Checa pasta no share do pacote ROS
        if HAS_AMENT:
            try:
                pkg_dir = get_package_share_directory('agv_brain')
                share_web = os.path.join(pkg_dir, 'web')
                if os.path.isdir(share_web):
                    return share_web
            except Exception:
                pass

        # 3. Fallback no workspace
        workspace_web = '/workspace/src/agv_brain/agv_brain/web'
        if os.path.isdir(workspace_web):
            return workspace_web

        return local_dir

    def _generate_standby_frames(self):
        """Gera imagem JPEG de standby com aviso amigável quando a câmera estiver desligada."""
        if not HAS_OPENCV:
            self.latest_raw_jpeg = b''
            self.latest_debug_jpeg = b''
            return

        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (18, 22, 28)

        # Desenha grade sutil
        for x in range(0, 640, 40):
            cv2.line(img, (x, 0), (x, 480), (28, 34, 44), 1)
        for y in range(0, 480, 40):
            cv2.line(img, (0, y), (640, y), (28, 34, 44), 1)

        # Moldura cibernética
        cv2.rectangle(img, (20, 20), (620, 460), (57, 197, 187), 2)
        cv2.circle(img, (320, 200), 45, (88, 166, 255), 2)
        cv2.line(img, (320, 140), (320, 260), (88, 166, 255), 1)
        cv2.line(img, (260, 200), (380, 200), (88, 166, 255), 1)

        cv2.putText(
            img, 'AGV CAMERA STANDBY', (160, 290),
            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (240, 246, 252), 2
        )
        cv2.putText(
            img, 'Aguardando transmissao de frames ROS 2...', (120, 330),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (139, 148, 158), 1
        )
        cv2.putText(
            img, 'Inicie a simulacao no Gazebo ou conecte a camera USB', (100, 360),
            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (57, 197, 187), 1
        )

        _, enc = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        self.latest_raw_jpeg = enc.tobytes()
        self.latest_debug_jpeg = self.latest_raw_jpeg

    # --- Callbacks de Imagem e Telemetria ---

    def _debug_image_callback(self, msg: Image):
        if not HAS_OPENCV or self.bridge is None:
            return
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            _, enc = cv2.imencode('.jpg', cv_img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            with self.frame_lock:
                self.latest_debug_jpeg = enc.tobytes()
                self.last_debug_time = time.time()
        except Exception as exc:
            self.get_logger().error(f'Falha ao converter line_debug_image: {exc}')

    def _raw_image_callback(self, msg: Image):
        if not HAS_OPENCV or self.bridge is None:
            return
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            _, enc = cv2.imencode('.jpg', cv_img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            with self.frame_lock:
                self.latest_raw_jpeg = enc.tobytes()
                self.last_raw_time = time.time()
        except Exception as exc:
            self.get_logger().error(f'Falha ao converter camera/image_raw: {exc}')

    def _line_error_callback(self, msg: Vector3):
        with self.telemetry_lock:
            self.telemetry['line_found'] = (msg.z > 0.5)
            self.telemetry['line_error'] = float(msg.x)
            self.telemetry['line_error_px'] = float(msg.y)
            self.telemetry['timestamp'] = time.time()

    def _state_callback(self, msg: String):
        with self.telemetry_lock:
            self.telemetry['state'] = msg.data.strip()
            self.telemetry['timestamp'] = time.time()

    def _obstacle_callback(self, msg: Bool):
        with self.telemetry_lock:
            self.telemetry['obstacle_detected'] = bool(msg.data)
            self.telemetry['timestamp'] = time.time()

    def _ultrasonic_callback(self, msg: Range):
        with self.telemetry_lock:
            self.telemetry['ultrasonic_distance'] = round(float(msg.range), 2)
            self.telemetry['timestamp'] = time.time()

    def _cmd_vel_callback(self, msg: Twist):
        with self.telemetry_lock:
            self.telemetry['linear_velocity'] = round(float(msg.linear.x), 2)
            self.telemetry['angular_velocity'] = round(float(msg.angular.z), 2)
            self.telemetry['timestamp'] = time.time()

    def _odom_callback(self, msg: Odometry):
        p = msg.pose.pose.position
        o = msg.pose.pose.orientation
        yaw = quaternion_to_yaw(o.x, o.y, o.z, o.w)
        with self.telemetry_lock:
            self.telemetry['odom_x'] = round(float(p.x), 3)
            self.telemetry['odom_y'] = round(float(p.y), 3)
            self.telemetry['odom_yaw'] = round(yaw, 3)
            self.telemetry['timestamp'] = time.time()

    def _battery_callback(self, msg: Float32):
        with self.telemetry_lock:
            self.telemetry['battery_voltage'] = round(float(msg.data), 1)
            self.telemetry['timestamp'] = time.time()

    # --- Comandos do Robô ---

    def send_mission_command(self, enable: bool):
        """Envia START ou STOP para o nó line_follower."""
        cmd_str = 'START' if enable else 'STOP'
        msg = String()
        msg.data = cmd_str
        self.cmd_pub.publish(msg)

        if self.srv_client.wait_for_service(timeout_sec=0.2):
            req = SetBool.Request()
            req.data = enable
            self.srv_client.call_async(req)

        self.get_logger().info(f'[WEB DASHBOARD] Comando publicado: {cmd_str}')

    def send_teleop_twist(self, linear_x: float, angular_z: float):
        """Publica comando de teleoperação manual em /cmd_vel_joy."""
        twist = Twist()
        twist.linear.x = float(linear_x)
        twist.angular.z = float(angular_z)
        self.teleop_pub.publish(twist)

    # --- Servidor HTTP ---

    def _run_http_server(self):
        node = self

        class DashboardHTTPHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Silencia logs comuns para manter o terminal limpo
                return

            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path

                # 1. API: Telemetria JSON
                if path == '/api/telemetry':
                    with node.telemetry_lock:
                        data = dict(node.telemetry)
                    payload = json.dumps(data).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                # 2. API: Transmissão MJPEG ao vivo (Debug HUD ou Raw)
                if path in ('/api/stream/debug', '/api/stream/raw', '/video_feed'):
                    is_raw = (path == '/api/stream/raw')
                    self.send_response(200)
                    self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('Expires', '0')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                    frame_interval = 1.0 / float(node.max_fps)
                    try:
                        while rclpy.ok():
                            start_t = time.time()
                            with node.frame_lock:
                                if is_raw:
                                    frame = node.latest_raw_jpeg
                                else:
                                    frame = node.latest_debug_jpeg

                            if frame:
                                header = (
                                    b'--frame\r\n'
                                    b'Content-Type: image/jpeg\r\n'
                                    b'Content-Length: ' + str(len(frame)).encode() + b'\r\n\r\n'
                                )
                                self.wfile.write(header)
                                self.wfile.write(frame)
                                self.wfile.write(b'\r\n')

                            elapsed = time.time() - start_t
                            sleep_t = max(0.01, frame_interval - elapsed)
                            time.sleep(sleep_t)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    return

                # 3. Arquivos Estáticos (index.html, style.css, app.js)
                req_file = path.lstrip('/')
                if not req_file or req_file == '/':
                    req_file = 'index.html'

                file_path = os.path.join(node.web_dir, req_file)

                # Tipos MIME
                mime = 'text/plain'
                if req_file.endswith('.html'):
                    mime = 'text/html; charset=utf-8'
                elif req_file.endswith('.css'):
                    mime = 'text/css; charset=utf-8'
                elif req_file.endswith('.js'):
                    mime = 'application/javascript; charset=utf-8'
                elif req_file.endswith('.svg'):
                    mime = 'image/svg+xml'
                elif req_file.endswith('.png'):
                    mime = 'image/png'
                elif req_file.endswith('.ico'):
                    mime = 'image/x-icon'

                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        self.send_response(200)
                        self.send_header('Content-Type', mime)
                        self.send_header('Content-Length', str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                        return
                    except Exception as exc:
                        node.get_logger().error(f'Erro ao ler arquivo web {file_path}: {exc}')

                # 404 Not Found
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'404 Not Found')

            def do_POST(self):
                parsed = urlparse(self.path)
                path = parsed.path
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'

                try:
                    data = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    data = {}

                # 1. Comando START / STOP
                if path == '/api/command':
                    action = str(data.get('action', '')).upper()
                    if action in ('START', 'GO', '1'):
                        node.send_mission_command(True)
                        resp = {'status': 'ok', 'action': 'START'}
                    elif action in ('STOP', '0'):
                        node.send_mission_command(False)
                        resp = {'status': 'ok', 'action': 'STOP'}
                    else:
                        resp = {'status': 'error', 'message': 'Acao desconhecida'}

                # 2. Teleoperação Manual
                elif path == '/api/teleop':
                    linear = float(data.get('linear', 0.0))
                    angular = float(data.get('angular', 0.0))
                    node.send_teleop_twist(linear, angular)
                    resp = {'status': 'ok', 'linear': linear, 'angular': angular}

                # 3. Parada de Emergência
                elif path == '/api/emergency':
                    node.send_mission_command(False)
                    node.send_teleop_twist(0.0, 0.0)
                    resp = {'status': 'ok', 'emergency': True}

                else:
                    self.send_response(404)
                    self.end_headers()
                    return

                res_bytes = json.dumps(resp).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(res_bytes)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(res_bytes)

        try:
            self.http_server = ThreadingHTTPServer((self.host, self.port), DashboardHTTPHandler)
            self.http_server.serve_forever()
        except Exception as exc:
            self.get_logger().error(f'Falha no servidor HTTP: {exc}')

    def destroy_node(self):
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WebDashboardNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
