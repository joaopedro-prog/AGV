#!/usr/bin/env python3
"""
teleop_joy_receiver.py
----------------------
Nó ROS 2 para Teleoperação via Joystick USB (Simulação e Robô Real).
Recebe comandos continuamente via:
 1) Standard Input (pipe direto do processo Windows via docker exec -i)
 2) Socket UDP na porta 9876 (para robô real via rede Wi-Fi / IP)

Publica mensagens geometry_msgs/msg/Twist no tópico /cmd_vel_joy
com taxa de 30Hz e watchdog de segurança (timeout de 0.5s).
"""

import sys
import os
import time
import json
import socket
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

UDP_PORT = 9876
WATCHDOG_TIMEOUT_SEC = 0.5
RATE_HZ = 30.0


class JoyTeleopReceiver(Node):
    def __init__(self):
        super().__init__('joy_teleop_receiver')
        
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel_joy', 10)
        
        self.target_linear_x = 0.0
        self.target_angular_z = 0.0
        self.emergency_stop = False
        self.last_packet_time = 0.0
        self.is_active = False
        self.running = True
        
        # Inicia leitor de stdin em thread separada
        self.stdin_thread = threading.Thread(target=self._stdin_loop, daemon=True)
        self.stdin_thread.start()
        
        # Inicia leitor UDP em thread separada (para robô real via Wi-Fi)
        self.udp_thread = threading.Thread(target=self._udp_loop, daemon=True)
        self.udp_thread.start()
        
        # Timer de controle a 30 Hz
        self.timer = self.create_timer(1.0 / RATE_HZ, self.timer_callback)
        
        self.get_logger().info("==================================================")
        self.get_logger().info(" [TELEOP JOY RECEIVER] Ativo e pronto!")
        self.get_logger().info(f" -> Entrada 1: Pipe stdin em tempo real")
        self.get_logger().info(f" -> Entrada 2: UDP 0.0.0.0:{UDP_PORT} (Robo Real Wi-Fi)")
        self.get_logger().info(" -> Publicando em: /cmd_vel_joy (Prioridade 100)")
        self.get_logger().info("==================================================")

    def _stdin_loop(self):
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line or not self.running:
                    continue
                # Formato aceito: "v,w" ou "v,w,stop" ou JSON {"v":0.5, "w":0.2, "stop":0}
                if line.startswith('{'):
                    try:
                        data = json.loads(line)
                        self.target_linear_x = float(data.get('v', 0.0))
                        self.target_angular_z = float(data.get('w', 0.0))
                        self.emergency_stop = bool(data.get('stop', False))
                        self.last_packet_time = time.time()
                    except Exception:
                        pass
                else:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            self.target_linear_x = float(parts[0])
                            self.target_angular_z = float(parts[1])
                            self.emergency_stop = bool(int(parts[2])) if len(parts) > 2 else False
                            self.last_packet_time = time.time()
                        except ValueError:
                            pass
        except Exception:
            pass

    def _udp_loop(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', UDP_PORT))
            while self.running:
                try:
                    data, _ = sock.recvfrom(1024)
                    text = data.decode('utf-8').strip()
                    if text.startswith('{'):
                        data_json = json.loads(text)
                        self.target_linear_x = float(data_json.get('v', 0.0))
                        self.target_angular_z = float(data_json.get('w', 0.0))
                        self.emergency_stop = bool(data_json.get('stop', False))
                        self.last_packet_time = time.time()
                    else:
                        parts = text.split(',')
                        if len(parts) >= 2:
                            self.target_linear_x = float(parts[0])
                            self.target_angular_z = float(parts[1])
                            self.emergency_stop = bool(int(parts[2])) if len(parts) > 2 else False
                            self.last_packet_time = time.time()
                except Exception:
                    time.sleep(0.01)
        except Exception as e:
            self.get_logger().warn(f"Nao foi possivel abrir socket UDP na porta {UDP_PORT}: {e}")

    def timer_callback(self):
        now = time.time()
        time_since_last = now - self.last_packet_time

        # Watchdog ou Parada de Emergência
        if self.emergency_stop or time_since_last > WATCHDOG_TIMEOUT_SEC:
            if self.is_active:
                stop_twist = Twist()
                self.publisher_.publish(stop_twist)
                self.is_active = False
                if self.emergency_stop:
                    self.get_logger().warn("[TELEOP] >> PARADA DE EMERGENCIA ATIVA! <<")
            return

        # Publica velocidade atual do joystick
        twist = Twist()
        twist.linear.x = self.target_linear_x
        twist.angular.z = self.target_angular_z
        self.publisher_.publish(twist)
        self.is_active = True

    def destroy_node(self):
        self.running = False
        try:
            stop_twist = Twist()
            self.publisher_.publish(stop_twist)
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = JoyTeleopReceiver()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except Exception:
                pass


if __name__ == '__main__':
    main()
