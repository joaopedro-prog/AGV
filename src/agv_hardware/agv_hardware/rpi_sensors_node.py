#!/usr/bin/env python3
"""
Nó para leitura de sensores e botões conectados diretamente na GPIO da Raspberry Pi.

Caso 'enable_gpio' esteja true na Raspberry Pi, lê:
  - Botão físico de START (envia 'START' em /agv/command)
  - Botão físico de EMERGÊNCIA/STOP (envia 'STOP' em /agv/command)
  - Sensor digital de presença/obstáculo (publica em /agv/obstacle_detected)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

try:
    import RPi.GPIO as GPIO
    HAS_RPI_GPIO = True
except ImportError:
    HAS_RPI_GPIO = False


class RpiSensorsNode(Node):
    def __init__(self):
        super().__init__('rpi_sensors')

        self.declare_parameter('enable_gpio', False)
        self.declare_parameter('poll_rate_hz', 20.0)
        self.declare_parameter('emergency_button_pin', 17)
        self.declare_parameter('start_button_pin', 27)
        self.declare_parameter('obstacle_sensor_pin', 22)

        self.enable_gpio: bool = self.get_parameter('enable_gpio').value
        self.poll_rate: float = float(self.get_parameter('poll_rate_hz').value)
        self.emergency_pin: int = int(self.get_parameter('emergency_button_pin').value)
        self.start_pin: int = int(self.get_parameter('start_button_pin').value)
        self.obstacle_pin: int = int(self.get_parameter('obstacle_sensor_pin').value)

        self.cmd_pub = self.create_publisher(String, '/agv/command', 10)
        self.obstacle_pub = self.create_publisher(Bool, '/agv/obstacle_detected', 10)

        self.gpio_active = False
        if self.enable_gpio:
            if HAS_RPI_GPIO:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.emergency_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(self.start_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(self.obstacle_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.gpio_active = True
                self.get_logger().info(
                    f'GPIO da Raspberry Pi configurada (Start={self.start_pin}, '
                    f'Stop={self.emergency_pin}, Obstaculo={self.obstacle_pin})'
                )
            else:
                self.get_logger().warn(
                    'enable_gpio=True mas biblioteca RPi.GPIO não está instalada neste ambiente.'
                )
        else:
            self.get_logger().info('Nó rpi_sensors pronto (GPIO desativada por padrão no YAML).')

        self.prev_start_pressed = False
        self.prev_stop_pressed = False
        self.timer = self.create_timer(1.0 / max(1.0, self.poll_rate), self.poll_gpio)

    def poll_gpio(self):
        if not self.gpio_active:
            return

        # Botões com Pull-Up (nível lógico 0 = pressionado)
        stop_pressed = (GPIO.input(self.emergency_pin) == 0)
        start_pressed = (GPIO.input(self.start_pin) == 0)
        obstacle_active = (GPIO.input(self.obstacle_pin) == 0)

        if stop_pressed and not self.prev_stop_pressed:
            msg = String()
            msg.data = 'STOP'
            self.cmd_pub.publish(msg)
            self.get_logger().warn('Botão físico de PARADA pressionado!')

        if start_pressed and not self.prev_start_pressed and not stop_pressed:
            msg = String()
            msg.data = 'START'
            self.cmd_pub.publish(msg)
            self.get_logger().info('Botão físico de START pressionado!')

        obs_msg = Bool()
        obs_msg.data = bool(obstacle_active)
        self.obstacle_pub.publish(obs_msg)

        self.prev_start_pressed = start_pressed
        self.prev_stop_pressed = stop_pressed

    def destroy_node(self):
        if self.gpio_active and HAS_RPI_GPIO:
            GPIO.cleanup()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RpiSensorsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
