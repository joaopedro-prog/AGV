#!/usr/bin/env python3
"""
Nó do Dashboard Web e Servidor HMI Completo do AGV.

Responsabilidades:
1. Coleta telemetria e sensores em tempo real:
   - /odom (Odometria e velocidade real)
   - /agv/state (FSM: IDLE, EM_MOVIMENTO, REMOTE_STOP_REQUESTED, STOP_CONFIRMED,
                 HARDWARE_ESTOP_ACTIVE, RECOVERY_PENDING)
   - /agv/battery_voltage (Tensão da bateria)
   - /agv/line_error (Erro lateral da linha)
   - /agv/hardware_status (Link serial, CRC16 e segurança ESP32)
   - /agv/obstacle_detected (Alerta de obstáculo)
   - /imu/data_raw (Acelerômetro + Giroscópio MPU6050 I2C)
   - /agv/ultrasonic_left e /agv/ultrasonic_right (2x HC-SR04 Frontais)
   - /agv/line_debug_image e /camera/image_raw (Stream MJPEG ao vivo na porta 8080)
2. Publica comandos do operador:
   - /agv/command: START / STOP
   - /cmd_vel_emergency: Parada imediata prioridade 255
   - /cmd_vel_joy: Teleoperação manual prioridade 100
   - Chama serviço /agv/reset_emergency para procedimento de rearme em 5 passos
3. Servidor HTTP multi-thread em http://0.0.0.0:8080 (API REST + MJPEG Stream).
"""

from collections import deque
import http.server
import json
import math
import os
import socketserver
import struct
import threading
import time
import urllib.parse
from typing import Any, Dict, Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu, JointState, Range
from std_msgs.msg import Bool, Float32, String
from std_srvs.srv import Trigger

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class DashboardNode(Node):
    WHEEL_RADIUS = 0.0762
    WHEEL_SEPARATION = 0.468
    HISTORY_RATE_HZ = 10.0
    HISTORY_MAX_LEN = 600

    def __init__(self):
        super().__init__('agv_dashboard_node')

        self.declare_parameter('web_port', 8080)
        self.port: int = int(self.get_parameter('web_port').value)

        self._lock = threading.Lock()
        self.start_time = time.monotonic()
        self.last_cam_time = 0.0
        self.last_debug_cam_time = 0.0
        self.last_imu_time = 0.0
        self.last_us_left_time = 0.0
        self.last_us_right_time = 0.0
        self.last_odom_time = 0.0
        self.last_line_time = 0.0
        self.last_cmd_line_time = 0.0
        self.last_cmd_joy_time = 0.0
        self.last_cmd_mux_time = 0.0
        self.last_joint_time = 0.0
        self.last_hw_time = 0.0
        self.last_state_time = 0.0
        self.last_relay_status_time = 0.0
        self._has_joint_vel = False

        self.latest_raw_jpeg: Optional[bytes] = None
        self.latest_debug_jpeg: Optional[bytes] = None
        self.history: deque = deque(maxlen=self.HISTORY_MAX_LEN)

        # Estado interno de telemetria
        self.telemetry: Dict[str, Any] = {
            'server_time_s': 0.0,
            'state': 'IDLE',
            'battery_v': 12.0,
            'obstacle': False,
            'line_error': 0.0,
            'line_cy': 0.0,
            'line_visible': False,
            'odom_x': 0.0,
            'odom_y': 0.0,
            'odom_yaw_deg': 0.0,
            'speed_lin': 0.0,
            'speed_ang': 0.0,
            'cmd_line_lin': 0.0,
            'cmd_line_ang': 0.0,
            'cmd_joy_lin': 0.0,
            'cmd_joy_ang': 0.0,
            'cmd_mux_lin': 0.0,
            'cmd_mux_ang': 0.0,
            'cmd_wheel_left_m_s': 0.0,
            'cmd_wheel_right_m_s': 0.0,
            'cmd_wheel_left_rad_s': 0.0,
            'cmd_wheel_right_rad_s': 0.0,
            'real_wheel_left_m_s': 0.0,
            'real_wheel_right_m_s': 0.0,
            'real_wheel_left_rad_s': 0.0,
            'real_wheel_right_rad_s': 0.0,
            'vel_error_lin': 0.0,
            'vel_error_ang': 0.0,
            'serial_connected': False,
            'odometry_valid': False,
            'safety_state': 'INIT',
            'crc_errors': 0,
            # Câmera
            'camera_active': False,
            'debug_cam_active': False,
            # IMU MPU6050
            'imu_active': False,
            'imu_ax': 0.0,
            'imu_ay': 0.0,
            'imu_az': 0.0,
            'imu_gx': 0.0,
            'imu_gy': 0.0,
            'imu_gz': 0.0,
            'imu_yaw_rate_deg': 0.0,
            # 2x Sensores Ultrassônicos Frontais (HC-SR04)
            'us_active': False,
            'us_left_m': None,
            'us_right_m': None,
            # Relés 12V Raspberry Pi (K1 Ventoinha BCM 17 / K2 Fita LED BCM 27)
            'fan_on': True,
            'led_on': True,
        }

        # Subscribers básicos
        self.sub_state = self.create_subscription(String, '/agv/state', self._state_cb, 10)
        self.sub_bat = self.create_subscription(Float32, '/agv/battery_voltage', self._bat_cb, 10)
        self.sub_obs = self.create_subscription(Bool, '/agv/obstacle_detected', self._obs_cb, 10)
        self.sub_error = self.create_subscription(Vector3, '/agv/line_error', self._error_cb, 10)
        self.sub_odom = self.create_subscription(Odometry, '/odom', self._odom_cb, 10)
        self.sub_hw = self.create_subscription(String, '/agv/hardware_status', self._hw_cb, 10)
        self.sub_relay_status = self.create_subscription(String, '/agv/relay_status', self._relay_status_cb, 10)

        # Subscribers de Comando / Cinemática / Juntas (para Osciloscópio por Node)
        self.sub_cmd_line = self.create_subscription(Twist, '/cmd_vel_line', self._cmd_line_cb, 10)
        self.sub_cmd_joy = self.create_subscription(Twist, '/cmd_vel_joy', self._cmd_joy_cb, 10)
        self.sub_cmd_mux_sim = self.create_subscription(Twist, '/cmd_vel', self._cmd_mux_cb, 10)
        self.sub_cmd_mux_hw = self.create_subscription(Twist, '/diff_cont/cmd_vel_unstamped', self._cmd_mux_cb, 10)
        self.sub_joint_states = self.create_subscription(JointState, '/joint_states', self._joint_states_cb, 10)

        # Subscribers de Sensores Ricos (Câmera, IMU e 2x Ultrassônicos Frontais)
        self.sub_cam_raw = self.create_subscription(Image, '/camera/image_raw', self._cam_raw_cb, 5)
        self.sub_cam_dbg = self.create_subscription(Image, '/agv/line_debug_image', self._cam_dbg_cb, 5)
        self.sub_imu = self.create_subscription(Imu, '/imu/data_raw', self._imu_cb, 10)
        self.sub_us_left = self.create_subscription(Range, '/agv/ultrasonic_left', self._us_left_cb, 10, raw=True)
        self.sub_us_right = self.create_subscription(Range, '/agv/ultrasonic_right', self._us_right_cb, 10, raw=True)

        # Publishers
        self.pub_cmd = self.create_publisher(String, '/agv/command', 10)
        self.pub_emergency = self.create_publisher(Twist, '/cmd_vel_emergency', 10)
        self.pub_teleop = self.create_publisher(Twist, '/cmd_vel_joy', 10)
        self.pub_relay_cmd = self.create_publisher(String, '/agv/relay_command', 10)

        # Service Client de Rearme
        self.cli_reset = self.create_client(Trigger, '/agv/reset_emergency')

        # Timer 10 Hz de amostragem histórica para os gráficos de escopo
        self.history_timer = self.create_timer(1.0 / self.HISTORY_RATE_HZ, self._record_history_tick)

        # Inicia Servidor HTTP Multi-Thread em thread separada
        self._start_http_server()

        self.get_logger().info(
            f'Dashboard Web Completo AGV iniciado na porta {self.port} '
            f'(API REST + MJPEG + IMU + 2x Ultrassônicos | OpenCV={HAS_CV2})!'
        )

    def _state_cb(self, msg: String):
        with self._lock:
            self.last_state_time = time.monotonic()
            self.telemetry['state'] = msg.data

    def _bat_cb(self, msg: Float32):
        with self._lock:
            self.telemetry['battery_v'] = round(msg.data, 2)

    def _obs_cb(self, msg: Bool):
        with self._lock:
            self.telemetry['obstacle'] = msg.data

    def _error_cb(self, msg: Vector3):
        with self._lock:
            self.last_line_time = time.monotonic()
            self.telemetry['line_error'] = round(msg.x, 3)
            self.telemetry['line_cy'] = round(msg.y, 1)
            self.telemetry['line_visible'] = (msg.z > 0.5)

    def _recompute_wheel_kinematics(self):
        """Calcula velocidades comandadas vs reais por roda (m/s e rad/s) e erros de rastreamento."""
        cmd_lin = float(self.telemetry['cmd_mux_lin'])
        cmd_ang = float(self.telemetry['cmd_mux_ang'])
        real_lin = float(self.telemetry['speed_lin'])
        real_ang = float(self.telemetry['speed_ang'])
        half_sep = self.WHEEL_SEPARATION * 0.5

        cmd_wl_ms = cmd_lin - (cmd_ang * half_sep)
        cmd_wr_ms = cmd_lin + (cmd_ang * half_sep)
        self.telemetry['cmd_wheel_left_m_s'] = round(cmd_wl_ms, 3)
        self.telemetry['cmd_wheel_right_m_s'] = round(cmd_wr_ms, 3)
        self.telemetry['cmd_wheel_left_rad_s'] = round(cmd_wl_ms / self.WHEEL_RADIUS, 3)
        self.telemetry['cmd_wheel_right_rad_s'] = round(cmd_wr_ms / self.WHEEL_RADIUS, 3)

        if (time.monotonic() - self.last_joint_time) > 0.5 or not self._has_joint_vel:
            real_wl_ms = real_lin - (real_ang * half_sep)
            real_wr_ms = real_lin + (real_ang * half_sep)
            self.telemetry['real_wheel_left_m_s'] = round(real_wl_ms, 3)
            self.telemetry['real_wheel_right_m_s'] = round(real_wr_ms, 3)
            self.telemetry['real_wheel_left_rad_s'] = round(real_wl_ms / self.WHEEL_RADIUS, 3)
            self.telemetry['real_wheel_right_rad_s'] = round(real_wr_ms / self.WHEEL_RADIUS, 3)

        self.telemetry['vel_error_lin'] = round(cmd_lin - real_lin, 3)
        self.telemetry['vel_error_ang'] = round(cmd_ang - real_ang, 3)

    def _odom_cb(self, msg: Odometry):
        qx = msg.pose.pose.orientation.x
        qy = msg.pose.pose.orientation.y
        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        yaw_deg = math.degrees(math.atan2(siny_cosp, cosy_cosp))

        with self._lock:
            self.last_odom_time = time.monotonic()
            self.telemetry['odom_x'] = round(msg.pose.pose.position.x, 2)
            self.telemetry['odom_y'] = round(msg.pose.pose.position.y, 2)
            self.telemetry['odom_yaw_deg'] = round(yaw_deg, 1)
            self.telemetry['speed_lin'] = round(msg.twist.twist.linear.x, 3)
            self.telemetry['speed_ang'] = round(msg.twist.twist.angular.z, 3)
            self._recompute_wheel_kinematics()

    def _cmd_line_cb(self, msg: Twist):
        with self._lock:
            self.last_cmd_line_time = time.monotonic()
            self.telemetry['cmd_line_lin'] = round(msg.linear.x, 3)
            self.telemetry['cmd_line_ang'] = round(msg.angular.z, 3)

    def _cmd_joy_cb(self, msg: Twist):
        with self._lock:
            self.last_cmd_joy_time = time.monotonic()
            self.telemetry['cmd_joy_lin'] = round(msg.linear.x, 3)
            self.telemetry['cmd_joy_ang'] = round(msg.angular.z, 3)

    def _cmd_mux_cb(self, msg: Twist):
        with self._lock:
            self.last_cmd_mux_time = time.monotonic()
            self.telemetry['cmd_mux_lin'] = round(msg.linear.x, 3)
            self.telemetry['cmd_mux_ang'] = round(msg.angular.z, 3)
            self._recompute_wheel_kinematics()

    def _joint_states_cb(self, msg: JointState):
        now = time.monotonic()
        with self._lock:
            self.last_joint_time = now
            got_vel = False
            for idx, name in enumerate(msg.name):
                if idx < len(msg.velocity):
                    vel = float(msg.velocity[idx])
                    lname = name.lower()
                    if 'left' in lname:
                        self.telemetry['real_wheel_left_rad_s'] = round(vel, 3)
                        self.telemetry['real_wheel_left_m_s'] = round(vel * self.WHEEL_RADIUS, 3)
                        got_vel = True
                    elif 'right' in lname:
                        self.telemetry['real_wheel_right_rad_s'] = round(vel, 3)
                        self.telemetry['real_wheel_right_m_s'] = round(vel * self.WHEEL_RADIUS, 3)
                        got_vel = True
            if got_vel:
                self._has_joint_vel = True

    def _hw_cb(self, msg: String):
        try:
            data = json.loads(msg.data)
            with self._lock:
                self.last_hw_time = time.monotonic()
                self.telemetry['serial_connected'] = data.get('serial_connected', False)
                self.telemetry['odometry_valid'] = data.get('odometry_valid', False)
                self.telemetry['safety_state'] = data.get('safety_state', 'UNKNOWN')
                self.telemetry['crc_errors'] = data.get('crc_errors', 0)
        except Exception:
            pass

    def _relay_status_cb(self, msg: String):
        try:
            data = json.loads(msg.data)
            with self._lock:
                self.last_relay_status_time = time.monotonic()
                if 'fan_on' in data:
                    self.telemetry['fan_on'] = bool(data['fan_on'])
                if 'led_on' in data:
                    self.telemetry['led_on'] = bool(data['led_on'])
        except Exception:
            pass

    def _encode_image_to_jpeg(self, msg: Image) -> Optional[bytes]:
        if not HAS_CV2 or msg.height == 0 or msg.width == 0:
            return None
        try:
            enc = msg.encoding.lower()
            arr = np.frombuffer(msg.data, dtype=np.uint8)
            if enc in ('bgr8', 'rgb8'):
                img = arr.reshape((msg.height, msg.step))[:, :msg.width * 3].reshape((msg.height, msg.width, 3))
                if enc == 'rgb8':
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif enc == 'mono8':
                gray = arr.reshape((msg.height, msg.step))[:, :msg.width]
                img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            else:
                return None

            ok, jpg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
            if ok:
                return jpg.tobytes()
        except Exception:
            pass
        return None

    def _cam_raw_cb(self, msg: Image):
        jpg = self._encode_image_to_jpeg(msg)
        if jpg is not None:
            with self._lock:
                self.latest_raw_jpeg = jpg
                self.last_cam_time = time.monotonic()

    def _cam_dbg_cb(self, msg: Image):
        jpg = self._encode_image_to_jpeg(msg)
        if jpg is not None:
            with self._lock:
                self.latest_debug_jpeg = jpg
                self.last_debug_cam_time = time.monotonic()

    def _imu_cb(self, msg: Imu):
        now = time.monotonic()
        with self._lock:
            self.last_imu_time = now
            self.telemetry['imu_ax'] = round(msg.linear_acceleration.x, 2)
            self.telemetry['imu_ay'] = round(msg.linear_acceleration.y, 2)
            self.telemetry['imu_az'] = round(msg.linear_acceleration.z, 2)
            self.telemetry['imu_gx'] = round(msg.angular_velocity.x, 3)
            self.telemetry['imu_gy'] = round(msg.angular_velocity.y, 3)
            self.telemetry['imu_gz'] = round(msg.angular_velocity.z, 3)
            self.telemetry['imu_yaw_rate_deg'] = round(math.degrees(msg.angular_velocity.z), 1)

    def _parse_range_m(self, raw_msg) -> Optional[float]:
        try:
            if isinstance(raw_msg, (bytes, bytearray, memoryview)):
                if len(raw_msg) < 16:
                    return None
                _, min_r, max_r, r = struct.unpack('<4f', bytes(raw_msg[-16:]))
            else:
                r = float(raw_msg.range)
                min_r = float(raw_msg.min_range)
                max_r = float(raw_msg.max_range)
            if math.isnan(r) or math.isinf(r) or r < min_r or r > max_r:
                return None
            return round(r, 2)
        except Exception:
            return None

    def _us_left_cb(self, msg: Range):
        val = self._parse_range_m(msg)
        with self._lock:
            self.last_us_left_time = time.monotonic()
            self.telemetry['us_left_m'] = val
            self._refresh_us_obstacle()

    def _us_right_cb(self, msg: Range):
        val = self._parse_range_m(msg)
        with self._lock:
            self.last_us_right_time = time.monotonic()
            self.telemetry['us_right_m'] = val
            self._refresh_us_obstacle()

    def _refresh_us_obstacle(self):
        l_val = self.telemetry['us_left_m']
        r_val = self.telemetry['us_right_m']
        l_blk = (l_val is not None and l_val < 0.25)
        r_blk = (r_val is not None and r_val < 0.25)
        self.telemetry['obstacle'] = bool(l_blk or r_blk)

    def _record_history_tick(self):
        now = time.monotonic()
        with self._lock:
            if (now - self.last_cmd_mux_time) > 0.8 and (
                self.telemetry['cmd_mux_lin'] != 0.0 or self.telemetry['cmd_mux_ang'] != 0.0
            ):
                self.telemetry['cmd_mux_lin'] = 0.0
                self.telemetry['cmd_mux_ang'] = 0.0
                self._recompute_wheel_kinematics()
            if (now - self.last_cmd_line_time) > 0.8:
                self.telemetry['cmd_line_lin'] = 0.0
                self.telemetry['cmd_line_ang'] = 0.0
            if (now - self.last_cmd_joy_time) > 0.8:
                self.telemetry['cmd_joy_lin'] = 0.0
                self.telemetry['cmd_joy_ang'] = 0.0

            t_rel = round(now - self.start_time, 3)
            self.telemetry['server_time_s'] = t_rel
            t = self.telemetry
            self.history.append({
                't': t_rel,
                'cmd_mux_lin': t['cmd_mux_lin'],
                'cmd_mux_ang': t['cmd_mux_ang'],
                'speed_lin': t['speed_lin'],
                'speed_ang': t['speed_ang'],
                'vel_error_lin': t['vel_error_lin'],
                'vel_error_ang': t['vel_error_ang'],
                'cmd_wheel_left_rad_s': t['cmd_wheel_left_rad_s'],
                'cmd_wheel_right_rad_s': t['cmd_wheel_right_rad_s'],
                'real_wheel_left_rad_s': t['real_wheel_left_rad_s'],
                'real_wheel_right_rad_s': t['real_wheel_right_rad_s'],
                'cmd_wheel_left_m_s': t['cmd_wheel_left_m_s'],
                'cmd_wheel_right_m_s': t['cmd_wheel_right_m_s'],
                'real_wheel_left_m_s': t['real_wheel_left_m_s'],
                'real_wheel_right_m_s': t['real_wheel_right_m_s'],
                'cmd_line_lin': t['cmd_line_lin'],
                'cmd_line_ang': t['cmd_line_ang'],
                'cmd_joy_lin': t['cmd_joy_lin'],
                'cmd_joy_ang': t['cmd_joy_ang'],
                'line_error': t['line_error'],
                'line_cy': t['line_cy'],
                'line_visible': 1 if t['line_visible'] else 0,
                'odom_x': t['odom_x'],
                'odom_y': t['odom_y'],
                'odom_yaw_deg': t['odom_yaw_deg'],
                'battery_v': t['battery_v'],
                'crc_errors': t['crc_errors'],
                'obstacle': 1 if t['obstacle'] else 0,
                'us_left_m': t['us_left_m'],
                'us_right_m': t['us_right_m'],
                'imu_ax': t['imu_ax'],
                'imu_ay': t['imu_ay'],
                'imu_az': t['imu_az'],
                'imu_gx': t['imu_gx'],
                'imu_gy': t['imu_gy'],
                'imu_gz': t['imu_gz'],
                'imu_yaw_rate_deg': t['imu_yaw_rate_deg'],
                'fan_on': 1 if t['fan_on'] else 0,
                'led_on': 1 if t['led_on'] else 0,
            })

    def get_history_snapshot(self, limit: int = 0) -> Dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            items = list(self.history)
            if limit > 0:
                items = items[-limit:]
            return {
                'server_time_s': round(now - self.start_time, 3),
                'samples': items,
            }

    def get_status_snapshot(self) -> Dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            snap = dict(self.telemetry)
            snap['server_time_s'] = round(now - self.start_time, 3)
            snap['camera_active'] = (now - self.last_cam_time) < 2.5
            snap['debug_cam_active'] = (now - self.last_debug_cam_time) < 2.5
            snap['imu_active'] = (now - self.last_imu_time) < 2.5
            snap['us_active'] = (
                (now - self.last_us_left_time) < 2.5
                or (now - self.last_us_right_time) < 2.5
            )
            snap['nodes_active'] = {
                'line_detector': (now - self.last_line_time) < 2.5,
                'line_follower': (now - self.last_cmd_line_time) < 2.5 or (now - self.last_state_time) < 2.5,
                'twist_mux': (now - self.last_cmd_mux_time) < 2.5,
                'odom': (now - self.last_odom_time) < 2.5,
                'joint_states': (now - self.last_joint_time) < 2.5,
                'serial_bridge': bool(self.telemetry['serial_connected']) or (now - self.last_hw_time) < 2.5,
                'rpi_sensors': (now - self.last_imu_time) < 2.5 or (now - self.last_relay_status_time) < 2.5,
                'ultrasonics': snap['us_active'],
                'camera': snap['camera_active'] or snap['debug_cam_active'],
            }
            return snap

    def get_camera_jpeg(self, prefer_raw: bool = False) -> Optional[bytes]:
        now = time.monotonic()
        with self._lock:
            if prefer_raw:
                return self.latest_raw_jpeg
            if self.latest_debug_jpeg is not None and (now - self.last_debug_cam_time) < 3.0:
                return self.latest_debug_jpeg
            return self.latest_raw_jpeg

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
            s = String()
            s.data = 'STOP'
            self.pub_cmd.publish(s)
            return {'status': 'ok', 'message': 'EMERGÊNCIA 255 acionada'}

        elif action == 'reset':
            if self.cli_reset.wait_for_service(timeout_sec=0.4):
                req = Trigger.Request()
                self.cli_reset.call_async(req)
                return {'status': 'ok', 'message': 'Solicitação de rearme transmitida ao ESP32'}
            # Fallback para simulação (sem serial_bridge): envia RESET via /agv/command
            s = String()
            s.data = 'RESET'
            self.pub_cmd.publish(s)
            return {'status': 'ok', 'message': 'Rearme enviado ao supervisor (modo simulação)'}

        elif action == 'teleop':
            v = float(params.get('linear', 0.0))
            w = float(params.get('angular', 0.0))
            t = Twist()
            t.linear.x = v
            t.angular.z = w
            self.pub_teleop.publish(t)
            return {'status': 'ok', 'message': 'Comando teleop publicado'}

        elif action == 'relay':
            target = str(params.get('target', '')).lower()
            state = params.get('state', None)
            with self._lock:
                if target == 'fan':
                    new_state = (not self.telemetry['fan_on']) if state is None else bool(state)
                    self.telemetry['fan_on'] = new_state
                elif target == 'led':
                    new_state = (not self.telemetry['led_on']) if state is None else bool(state)
                    self.telemetry['led_on'] = new_state
                else:
                    return {'status': 'error', 'message': f'Relé desconhecido: {target}'}
                fan_on = bool(self.telemetry['fan_on'])
                led_on = bool(self.telemetry['led_on'])

            cmd_msg = String()
            cmd_msg.data = json.dumps({
                'target': target,
                'state': bool(new_state),
                'fan': fan_on,
                'led': led_on,
            })
            self.pub_relay_cmd.publish(cmd_msg)
            label = 'Ventoinha (K1)' if target == 'fan' else 'Fita LED 12V (K2)'
            return {
                'status': 'ok',
                'target': target,
                'state': bool(new_state),
                'fan_on': fan_on,
                'led_on': led_on,
                'message': f"{label} {'LIGADA' if new_state else 'DESLIGADA'}",
            }

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
                parsed = urllib.parse.urlsplit(self.path)
                route = parsed.path
                query = urllib.parse.parse_qs(parsed.query)
                prefer_raw = (query.get('raw', ['0'])[0] == '1')

                if route == '/api/status':
                    payload = json.dumps(node_ref.get_status_snapshot()).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if route == '/api/telemetry_history':
                    try:
                        limit = int(query.get('limit', ['0'])[0])
                    except ValueError:
                        limit = 0
                    payload = json.dumps(node_ref.get_history_snapshot(limit=limit)).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if route == '/api/camera_frame.jpg':
                    jpg = node_ref.get_camera_jpeg(prefer_raw=prefer_raw)
                    if jpg is None:
                        self.send_response(404)
                        self.end_headers()
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Content-Length', str(len(jpg)))
                    self.end_headers()
                    self.wfile.write(jpg)
                    return

                if route == '/api/camera_stream':
                    self.send_response(200)
                    self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    try:
                        while rclpy.ok():
                            jpg = node_ref.get_camera_jpeg(prefer_raw=prefer_raw)
                            if jpg is not None:
                                header = (
                                    b'--frame\r\n'
                                    b'Content-Type: image/jpeg\r\n'
                                    + f'Content-Length: {len(jpg)}\r\n\r\n'.encode('ascii')
                                )
                                self.wfile.write(header + jpg + b'\r\n')
                                self.wfile.flush()
                            time.sleep(0.066)
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass
                    return

                super().do_GET()

            def do_POST(self):
                parsed = urllib.parse.urlsplit(self.path)
                if parsed.path == '/api/command':
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode('utf-8')
                    try:
                        data = json.loads(body)
                        action = data.get('action', '')
                        res = node_ref.handle_user_command(action, data)
                        payload = json.dumps(res).encode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(payload)))
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(payload)
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
            with ThreadingHTTPServer(('0.0.0.0', self.port), CustomHandler) as httpd:
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
