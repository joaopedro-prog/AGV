#!/usr/bin/env python3
"""
Nó de Controle de GPIO e IMU da Raspberry Pi 3B (KiCad Rev 2.0).

Responsabilidades em conformidade com o esquemático KiCad Rev 2.0:
  1. Acionamento dos Relés 12V via transistores BC547:
     - Relé K1 (BCM GPIO 17 / CTRL_FAN): Ventoinhas de arrefecimento (Fan #1 e Fan #2).
     - Relé K2 (BCM GPIO 27 / CTRL_LED): Fita LED 5050 12V (contínua em operação normal,
       piscante em estado de emergência ou parada remota).
  2. Leitura opcional não-bloqueante do IMU MPU6050 via barramento I2C (/dev/i2c-1,
     BCM 2 SDA / BCM 3 SCL, endereço 0x68), publicando sensor_msgs/msg/Imu em /imu/data_raw.
  3. Leitura opcional de botões/sensores digitais extras caso pinos >= 0 sejam configurados.
"""

import json
import math
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu
from std_msgs.msg import Bool, String

try:
    import RPi.GPIO as GPIO
    HAS_RPI_GPIO = True
except ImportError:
    HAS_RPI_GPIO = False

try:
    import smbus
    HAS_SMBUS = True
except ImportError:
    try:
        import smbus2 as smbus
        HAS_SMBUS = True
    except ImportError:
        HAS_SMBUS = False


def _to_signed_16(high_byte: int, low_byte: int) -> int:
    val = (high_byte << 8) | low_byte
    return val - 65536 if val >= 32768 else val


class RpiSensorsNode(Node):
    MPU6050_ADDR = 0x68
    MPU6050_PWR_MGMT_1 = 0x6B
    MPU6050_ACCEL_XOUT_H = 0x3B

    def __init__(self):
        super().__init__('rpi_sensors')

        # Parâmetros de GPIO (KiCad Rev 2.0: BCM 17 = CTRL_FAN, BCM 27 = CTRL_LED)
        self.declare_parameter('enable_gpio', False)
        self.declare_parameter('poll_rate_hz', 20.0)
        self.declare_parameter('fan_relay_pin', 17)
        self.declare_parameter('led_relay_pin', 27)
        self.declare_parameter('auto_fan_enable', True)

        # Pinos opcionais de entrada (-1 = desativado, evita conflito com K1/K2)
        self.declare_parameter('emergency_button_pin', -1)
        self.declare_parameter('start_button_pin', -1)
        self.declare_parameter('obstacle_sensor_pin', -1)

        # Parâmetros IMU MPU6050 (I2C BCM 2/3 -> /dev/i2c-1)
        self.declare_parameter('enable_imu', True)
        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('imu_address', 0x68)
        self.declare_parameter('imu_frame_id', 'base_link')

        self.enable_gpio: bool = bool(self.get_parameter('enable_gpio').value)
        self.poll_rate: float = float(self.get_parameter('poll_rate_hz').value)
        self.fan_pin: int = int(self.get_parameter('fan_relay_pin').value)
        self.led_pin: int = int(self.get_parameter('led_relay_pin').value)
        self.auto_fan: bool = bool(self.get_parameter('auto_fan_enable').value)

        self.emergency_pin: int = int(self.get_parameter('emergency_button_pin').value)
        self.start_pin: int = int(self.get_parameter('start_button_pin').value)
        self.obstacle_pin: int = int(self.get_parameter('obstacle_sensor_pin').value)

        self.enable_imu: bool = bool(self.get_parameter('enable_imu').value)
        self.i2c_bus_num: int = int(self.get_parameter('i2c_bus').value)
        self.imu_addr: int = int(self.get_parameter('imu_address').value)
        self.imu_frame_id: str = str(self.get_parameter('imu_frame_id').value)

        # Publishers
        self.cmd_pub = self.create_publisher(String, '/agv/command', 10)
        self.obstacle_pub = self.create_publisher(Bool, '/agv/obstacle_detected', 10)
        self.emergency_pub = self.create_publisher(Twist, '/cmd_vel_emergency', 10)
        self.imu_pub = self.create_publisher(Imu, '/imu/data_raw', 10)

        # Subscribers de Estado para controle visual do Relé K2 (Fita LED 12V)
        self.agv_state = 'IDLE'
        self.hw_safety_state = 'INIT'
        self.sub_state = self.create_subscription(String, '/agv/state', self._state_cb, 10)
        self.sub_hw = self.create_subscription(String, '/agv/hardware_status', self._hw_status_cb, 10)

        # Inicialização GPIO Raspberry Pi 3B
        self.gpio_active = False
        self.led_output_state = False
        self.last_blink_time = time.monotonic()
        if self.enable_gpio:
            if HAS_RPI_GPIO:
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                if self.fan_pin >= 0:
                    GPIO.setup(self.fan_pin, GPIO.OUT, initial=GPIO.HIGH if self.auto_fan else GPIO.LOW)
                if self.led_pin >= 0:
                    GPIO.setup(self.led_pin, GPIO.OUT, initial=GPIO.HIGH)
                if self.emergency_pin >= 0:
                    GPIO.setup(self.emergency_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                if self.start_pin >= 0:
                    GPIO.setup(self.start_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                if self.obstacle_pin >= 0:
                    GPIO.setup(self.obstacle_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.gpio_active = True
                self.get_logger().info(
                    f'GPIO RPi ativa | Relé K1 Fan=BCM{self.fan_pin} | Relé K2 LED=BCM{self.led_pin}'
                )
            else:
                self.get_logger().warn(
                    'enable_gpio=True mas RPi.GPIO não está disponível neste ambiente.'
                )
        else:
            self.get_logger().info('Nó rpi_sensors pronto (enable_gpio=False).')

        # Inicialização MPU6050 I2C (com fallback seguro)
        self.bus: Optional[object] = None
        self.imu_active = False
        self.imu_fail_count = 0
        if self.enable_imu:
            self._init_imu()

        self.prev_start_pressed = False
        self.prev_stop_pressed = False
        self.timer = self.create_timer(1.0 / max(1.0, self.poll_rate), self.poll_loop)

    def _init_imu(self):
        if not HAS_SMBUS:
            self.get_logger().info('Biblioteca smbus ausente; leitura I2C MPU6050 desabilitada.')
            return
        try:
            self.bus = smbus.SMBus(self.i2c_bus_num)
            # Acorda o MPU6050 (PWR_MGMT_1 = 0x00), config ±2g e ±250 deg/s
            self.bus.write_byte_data(self.imu_addr, self.MPU6050_PWR_MGMT_1, 0x00)
            self.imu_active = True
            self.get_logger().info(
                f'IMU MPU6050 inicializado em /dev/i2c-{self.i2c_bus_num} (0x{self.imu_addr:02X})'
            )
        except Exception as exc:
            self.bus = None
            self.imu_active = False
            self.get_logger().warn(
                f'MPU6050 indisponível em /dev/i2c-{self.i2c_bus_num}: {exc}. Seguindo sem IMU.'
            )

    def _state_cb(self, msg: String):
        self.agv_state = msg.data.strip().upper()

    def _hw_status_cb(self, msg: String):
        try:
            data = json.loads(msg.data)
            self.hw_safety_state = str(data.get('safety_state', 'UNKNOWN')).upper()
        except Exception:
            pass

    def _update_relays(self):
        if not self.gpio_active or not HAS_RPI_GPIO:
            return

        # K1 (Ventoinhas Fan #1 e Fan #2)
        if self.fan_pin >= 0:
            GPIO.output(self.fan_pin, GPIO.HIGH if self.auto_fan else GPIO.LOW)

        # K2 (Fita LED 12V): pisca em alerta de emergência / parada, contínuo em operação normal
        if self.led_pin >= 0:
            is_alert = (
                'ESTOP' in self.agv_state
                or 'ESTOP' in self.hw_safety_state
                or self.agv_state in ('REMOTE_STOP_REQUESTED', 'RECOVERY_PENDING')
                or self.hw_safety_state in ('WATCHDOG_TIMEOUT', 'DRIVER_FAULT')
            )
            if is_alert:
                now = time.monotonic()
                if (now - self.last_blink_time) >= 0.25:
                    self.last_blink_time = now
                    self.led_output_state = not self.led_output_state
                GPIO.output(self.led_pin, GPIO.HIGH if self.led_output_state else GPIO.LOW)
            else:
                self.led_output_state = True
                GPIO.output(self.led_pin, GPIO.HIGH)

    def _poll_optional_inputs(self):
        if not self.gpio_active or not HAS_RPI_GPIO:
            return

        stop_pressed = (self.emergency_pin >= 0 and GPIO.input(self.emergency_pin) == 0)
        start_pressed = (self.start_pin >= 0 and GPIO.input(self.start_pin) == 0)

        if stop_pressed:
            self.emergency_pub.publish(Twist())
            if not self.prev_stop_pressed:
                msg = String()
                msg.data = 'STOP'
                self.cmd_pub.publish(msg)
                self.get_logger().warn('Entrada GPIO STOP acionada! Publicando /cmd_vel_emergency.')

        if start_pressed and not self.prev_start_pressed and not stop_pressed:
            msg = String()
            msg.data = 'START'
            self.cmd_pub.publish(msg)
            self.get_logger().info('Entrada GPIO START acionada!')

        if self.obstacle_pin >= 0:
            obs_msg = Bool()
            obs_msg.data = (GPIO.input(self.obstacle_pin) == 0)
            self.obstacle_pub.publish(obs_msg)

        self.prev_start_pressed = start_pressed
        self.prev_stop_pressed = stop_pressed

    def _poll_imu(self):
        if not self.imu_active or self.bus is None:
            return
        try:
            raw = self.bus.read_i2c_block_data(self.imu_addr, self.MPU6050_ACCEL_XOUT_H, 14)
            ax = (_to_signed_16(raw[0], raw[1]) / 16384.0) * 9.80665
            ay = (_to_signed_16(raw[2], raw[3]) / 16384.0) * 9.80665
            az = (_to_signed_16(raw[4], raw[5]) / 16384.0) * 9.80665

            gx = (_to_signed_16(raw[8], raw[9]) / 131.0) * (math.pi / 180.0)
            gy = (_to_signed_16(raw[10], raw[11]) / 131.0) * (math.pi / 180.0)
            gz = (_to_signed_16(raw[12], raw[13]) / 131.0) * (math.pi / 180.0)

            imu_msg = Imu()
            imu_msg.header.stamp = self.get_clock().now().to_msg()
            imu_msg.header.frame_id = self.imu_frame_id
            imu_msg.orientation_covariance[0] = -1.0  # IMU 6-DOF sem magnetômetro
            imu_msg.angular_velocity.x = gx
            imu_msg.angular_velocity.y = gy
            imu_msg.angular_velocity.z = gz
            imu_msg.linear_acceleration.x = ax
            imu_msg.linear_acceleration.y = ay
            imu_msg.linear_acceleration.z = az
            self.imu_pub.publish(imu_msg)
            self.imu_fail_count = 0
        except Exception as exc:
            self.imu_fail_count += 1
            if self.imu_fail_count == 5:
                self.get_logger().warn(f'Falha repetida na leitura I2C MPU6050: {exc}. Pausando IMU.')
                self.imu_active = False

    def poll_loop(self):
        self._update_relays()
        self._poll_optional_inputs()
        self._poll_imu()

    def destroy_node(self):
        if self.gpio_active and HAS_RPI_GPIO:
            try:
                if self.fan_pin >= 0:
                    GPIO.output(self.fan_pin, GPIO.LOW)
                if self.led_pin >= 0:
                    GPIO.output(self.led_pin, GPIO.LOW)
                GPIO.cleanup()
            except Exception:
                pass
        if self.bus is not None:
            try:
                self.bus.close()
            except Exception:
                pass
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
