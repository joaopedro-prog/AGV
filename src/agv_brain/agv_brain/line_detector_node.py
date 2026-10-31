#!/usr/bin/env python3
"""
Nó de Visão Computacional para Detecção de Linha (OpenCV + ROS 2).

Funciona de forma idêntica na Simulação (Gazebo) e no Robô Real (Raspberry Pi),
pois ambos publicam a imagem bruta em /camera/image_raw.

Publica:
  - /agv/line_error (geometry_msgs/Vector3):
      x: erro lateral normalizado [-1.0 = extrema esquerda, 0.0 = centro, +1.0 = extrema direita]
      y: erro lateral bruto em pixels
      z: 1.0 se a linha está visível, 0.0 se a linha foi perdida
  - /agv/line_debug_image (sensor_msgs/Image):
      Imagem com HUD visual mostrando o contorno da linha, centróide e erro atual.
"""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class LineDetectorNode(Node):
    def __init__(self):
        super().__init__('line_detector')

        # Parâmetros configuráveis via brain_params.yaml
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('publish_debug_image', True)
        self.declare_parameter('detection_mode', 'dark_line')
        self.declare_parameter('dark_threshold', 90)
        self.declare_parameter('hsv_lower', [20, 100, 100])
        self.declare_parameter('hsv_upper', [35, 255, 255])
        self.declare_parameter('roi_top_ratio', 0.50)
        self.declare_parameter('roi_bottom_ratio', 0.98)
        self.declare_parameter('min_contour_area', 150.0)

        image_topic = self.get_parameter('image_topic').value
        self.publish_debug = self.get_parameter('publish_debug_image').value

        self.bridge = CvBridge()

        # Subscriber da câmera (simulada ou real)
        self.image_sub = self.create_subscription(
            Image, image_topic, self.image_callback, 10
        )

        # Publishers
        self.error_pub = self.create_publisher(Vector3, '/agv/line_error', 10)
        self.debug_pub = self.create_publisher(Image, '/agv/line_debug_image', 10)

        self.get_logger().info(
            f'LineDetectorNode iniciado | Escutando: {image_topic} | '
            f'Modo: {self.get_parameter("detection_mode").value}'
        )

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'Falha no cv_bridge: {exc}')
            return

        height, width, _ = frame.shape

        # Lê parâmetros em tempo real (permite ajuste dinâmico com ros2 param set)
        mode = self.get_parameter('detection_mode').value
        dark_thresh = int(self.get_parameter('dark_threshold').value)
        hsv_lower = np.array(self.get_parameter('hsv_lower').value, dtype=np.uint8)
        hsv_upper = np.array(self.get_parameter('hsv_upper').value, dtype=np.uint8)
        roi_top = float(self.get_parameter('roi_top_ratio').value)
        roi_bottom = float(self.get_parameter('roi_bottom_ratio').value)
        min_area = float(self.get_parameter('min_contour_area').value)

        y_start = max(0, min(height - 2, int(height * roi_top)))
        y_end = max(y_start + 1, min(height, int(height * roi_bottom)))

        roi = frame[y_start:y_end, :]
        blurred = cv2.GaussianBlur(roi, (5, 5), 0)

        # Segmentação da linha no chão
        if mode == 'hsv':
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
        else:
            # 'dark_line': fita escura/preta em chão mais claro
            gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, dark_thresh, 255, cv2.THRESH_BINARY_INV)

        # Limpeza morfológica para remover ruídos do piso
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Busca contornos da fita
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        line_found = False
        error_norm = 0.0
        error_px = 0.0
        cx_global = width // 2
        cy_global = (y_start + y_end) // 2
        best_contour = None

        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area >= min_area:
                moments = cv2.moments(largest)
                if moments['m00'] > 0:
                    cx_roi = int(moments['m10'] / moments['m00'])
                    cy_roi = int(moments['m01'] / moments['m00'])
                    cx_global = cx_roi
                    cy_global = y_start + cy_roi

                    center_x = width * 0.5
                    error_px = float(cx_global - center_x)
                    error_norm = float(error_px / center_x)
                    line_found = True
                    best_contour = largest

        # Publica o vetor de erro para o controlador PID
        err_msg = Vector3()
        err_msg.x = float(error_norm)
        err_msg.y = float(error_px)
        err_msg.z = 1.0 if line_found else 0.0
        self.error_pub.publish(err_msg)

        # Publica imagem de debug se habilitado
        if self.publish_debug:
            debug_frame = frame.copy()
            # Desenha caixa da ROI e linha central de referência
            cv2.rectangle(debug_frame, (0, y_start), (width - 1, y_end - 1), (255, 200, 0), 2)
            cv2.line(debug_frame, (width // 2, y_start), (width // 2, y_end), (255, 0, 0), 2)

            if line_found and best_contour is not None:
                shifted_contour = best_contour + np.array([[[0, y_start]]])
                cv2.drawContours(debug_frame, [shifted_contour], -1, (0, 255, 0), 2)
                cv2.circle(debug_frame, (cx_global, cy_global), 8, (0, 0, 255), -1)
                cv2.line(debug_frame, (width // 2, cy_global), (cx_global, cy_global), (0, 255, 255), 2)
                status_text = f'LINHA OK | Erro: {error_norm:+.2f} ({int(error_px)} px)'
                color = (0, 255, 0)
            else:
                status_text = 'LINHA PERDIDA'
                color = (0, 0, 255)

            cv2.putText(
                debug_frame, status_text, (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2
            )

            debug_msg = self.bridge.cv2_to_imgmsg(debug_frame, encoding='bgr8')
            debug_msg.header = msg.header
            self.debug_pub.publish(debug_msg)


def main(args=None):
    rclpy.init(args=args)
    node = LineDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
