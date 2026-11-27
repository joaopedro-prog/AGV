#!/usr/bin/env python3
"""
Nó de Visão Computacional para Detecção de Linha do AGV (OpenCV + ROS 2).
Otimizado para o perfil de hardware da Raspberry Pi 3B (Quad-Core Cortex-A53).

Responsabilidades:
1. Recebe frames da câmera (/camera/image_raw).
2. Isola Região de Interesse (ROI) compacta no chão à frente do robô (ex: 320x60 px).
3. Normaliza contraste e segmenta a linha preta ou colorida com operações morfológicas rápidas.
4. Calcula centróide e publica o erro lateral normalizado [-1.0..+1.0] em /agv/line_error.
5. Mede o tempo de processamento por quadro e valida o SLO de latência (meta <= 20 ms).
6. Publica HUD gráfico em /agv/line_debug_image para monitoramento remoto.
"""

import time
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

        # Parâmetros configuráveis
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('publish_debug_image', True)
        self.declare_parameter('detection_mode', 'dark_line')
        self.declare_parameter('dark_threshold', 95)
        self.declare_parameter('min_contrast', 20.0)
        self.declare_parameter('hsv_lower', [20, 100, 100])
        self.declare_parameter('hsv_upper', [35, 255, 255])
        self.declare_parameter('roi_top_ratio', 0.50)
        self.declare_parameter('roi_bottom_ratio', 0.85)
        self.declare_parameter('min_contour_area', 40.0)
        self.declare_parameter('max_contour_area_ratio', 0.80)

        image_topic = self.get_parameter('image_topic').value
        self.publish_debug = self.get_parameter('publish_debug_image').value
        self.bridge = CvBridge()

        # Inscrição na câmera
        self.image_sub = self.create_subscription(
            Image, image_topic, self.image_callback, 10
        )

        # Publicações
        self.error_pub = self.create_publisher(Vector3, '/agv/line_error', 10)
        self.debug_pub = self.create_publisher(Image, '/agv/line_debug_image', 10)

        # Métricas de benchmark para RPi 3B
        self.frame_count = 0
        self.total_proc_time_ms = 0.0

        self.get_logger().info(
            f'LineDetectorNode otimizado para RPi 3B | Escutando: {image_topic} | '
            f'Modo: {self.get_parameter("detection_mode").value} | Meta Latência <= 20ms'
        )

    def image_callback(self, msg: Image):
        t_start = time.perf_counter()

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'Falha no cv_bridge: {exc}')
            return

        height, width, _ = frame.shape

        mode = self.get_parameter('detection_mode').value
        dark_thresh = int(self.get_parameter('dark_threshold').value)
        min_contrast = float(self.get_parameter('min_contrast').value)
        hsv_lower = np.array(self.get_parameter('hsv_lower').value, dtype=np.uint8)
        hsv_upper = np.array(self.get_parameter('hsv_upper').value, dtype=np.uint8)
        roi_top = float(self.get_parameter('roi_top_ratio').value)
        roi_bottom = float(self.get_parameter('roi_bottom_ratio').value)
        min_area = float(self.get_parameter('min_contour_area').value)
        max_area_ratio = float(self.get_parameter('max_contour_area_ratio').value)

        # 1. Recorte da Região de Interesse (ROI) compacta no chão
        y_start = max(0, min(height - 2, int(height * roi_top)))
        y_end = max(y_start + 1, min(height, int(height * roi_bottom)))
        roi = frame[y_start:y_end, :]
        roi_h, roi_w, _ = roi.shape
        roi_total_area = float(roi_h * roi_w)

        # Filtro rápido 3x3 (mais leve na CPU que 5x5)
        blurred = cv2.GaussianBlur(roi, (3, 3), 0)

        # 2. Segmentação da linha
        if mode == 'hsv':
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
            has_contrast = True
        else:
            gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
            min_val, max_val, _, _ = cv2.minMaxLoc(gray)
            contrast = max_val - min_val

            if contrast < min_contrast:
                mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
                has_contrast = False
            else:
                has_contrast = True
                gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
                thresh = dark_thresh if dark_thresh > 0 else 85
                _, mask = cv2.threshold(gray_norm, thresh, 255, cv2.THRESH_BINARY_INV)

        # 3. Operação morfológica 3x3 leve
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 4. Detecção de contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        line_found = False
        error_norm = 0.0
        error_px = 0.0
        cx_global = width // 2
        cy_global = (y_start + y_end) // 2
        best_contour = None
        max_allowed_area = roi_total_area * max_area_ratio

        if has_contrast and contours:
            valid_contours = []
            for c in contours:
                a = cv2.contourArea(c)
                if min_area <= a <= max_allowed_area:
                    valid_contours.append((c, a))

            if valid_contours:
                largest_c, _ = max(valid_contours, key=lambda item: item[1])
                moments = cv2.moments(largest_c)
                if moments['m00'] > 0:
                    cx_roi = int(moments['m10'] / moments['m00'])
                    cy_roi = int(moments['m01'] / moments['m00'])
                    cx_global = cx_roi
                    cy_global = y_start + cy_roi

                    center_x = width * 0.5
                    error_px = float(cx_global - center_x)
                    error_norm = float(error_px / center_x)
                    line_found = True
                    best_contour = largest_c

        # 5. Publicação do erro de linha
        err_msg = Vector3()
        err_msg.x = float(error_norm) if line_found else 0.0
        err_msg.y = float(error_px) if line_found else 0.0
        err_msg.z = 1.0 if line_found else 0.0
        self.error_pub.publish(err_msg)

        # 6. Avaliação de Latência do Quadro (Meta <= 20 ms)
        proc_time_ms = (time.perf_counter() - t_start) * 1000.0
        self.frame_count += 1
        self.total_proc_time_ms += proc_time_ms

        if self.frame_count % 100 == 0:
            avg_ms = self.total_proc_time_ms / self.frame_count
            if avg_ms > 20.0:
                self.get_logger().warn(
                    f'[SLO ALERTA] Latência média de visão: {avg_ms:.2f} ms > 20 ms na RPi 3B!'
                )

        # 7. Construção do HUD gráfico para RViz/Dashboard
        if self.publish_debug:
            debug_frame = frame.copy()
            box_color = (0, 255, 0) if line_found else (0, 0, 255)
            cv2.rectangle(debug_frame, (0, y_start), (width - 1, y_end - 1), box_color, 2)
            cv2.line(debug_frame, (width // 2, y_start), (width // 2, y_end), (255, 200, 0), 2)

            if line_found and best_contour is not None:
                shifted_contour = best_contour + np.array([[[0, y_start]]])
                cv2.drawContours(debug_frame, [shifted_contour], -1, (0, 255, 0), 2)
                cv2.circle(debug_frame, (cx_global, cy_global), 6, (0, 0, 255), -1)
                cv2.line(debug_frame, (width // 2, cy_global), (cx_global, cy_global), (0, 255, 255), 2)
                direction_str = "DIR" if error_norm > 0.05 else ("ESQ" if error_norm < -0.05 else "CENTRO")
                status_text = f"LINHA OK | Erro: {error_norm:+.2f} ({direction_str}) | Lat: {proc_time_ms:.1f}ms"
                text_color = (0, 255, 0)
            else:
                status_text = f"BUSCANDO LINHA... | Lat: {proc_time_ms:.1f}ms"
                text_color = (0, 0, 255)

            cv2.rectangle(debug_frame, (0, 0), (width, 36), (0, 0, 0), -1)
            cv2.putText(
                debug_frame, status_text, (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2
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
