#!/usr/bin/env python3
"""
Nó de Visão Computacional para Detecção de Linha do AGV (OpenCV + ROS 2).

Responsabilidades:
1. Recebe frames da câmera (/camera/image_raw).
2. Isola a Região de Interesse (ROI) no chão à frente do robô.
3. Verifica contraste dinâmico para não confundir sombras ou chão homogêneo com linha.
4. Normaliza o contraste e segmenta a linha preta (dark_line) ou fita colorida (hsv).
5. Filtra ruídos pequenos e descarta áreas gigantes (evita que a tela inteira seja detectada como erro zero).
6. Calcula o centróide e publica o erro lateral normalizado [-1.0..+1.0] em /agv/line_error.
7. Publica o stream com HUD gráfico completo em /agv/line_debug_image.
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

        # Parâmetros configuráveis
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('publish_debug_image', True)
        self.declare_parameter('detection_mode', 'dark_line')
        self.declare_parameter('dark_threshold', 95)
        self.declare_parameter('min_contrast', 20.0)
        self.declare_parameter('hsv_lower', [20, 100, 100])
        self.declare_parameter('hsv_upper', [35, 255, 255])
        self.declare_parameter('roi_top_ratio', 0.40)
        self.declare_parameter('roi_bottom_ratio', 0.95)
        self.declare_parameter('min_contour_area', 50.0)
        self.declare_parameter('max_contour_area_ratio', 0.85)

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

        try:
            if cv2.ocl.haveOpenCL():
                cv2.ocl.setUseOpenCL(True)
                self.get_logger().info('OpenCV Aceleracao: OpenCL GPU Ativado')
            else:
                cv2.setNumThreads(4)
        except Exception:
            pass

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

        # Parâmetros dinâmicos
        mode = self.get_parameter('detection_mode').value
        dark_thresh = int(self.get_parameter('dark_threshold').value)
        min_contrast = float(self.get_parameter('min_contrast').value)
        hsv_lower = np.array(self.get_parameter('hsv_lower').value, dtype=np.uint8)
        hsv_upper = np.array(self.get_parameter('hsv_upper').value, dtype=np.uint8)
        roi_top = float(self.get_parameter('roi_top_ratio').value)
        roi_bottom = float(self.get_parameter('roi_bottom_ratio').value)
        min_area = float(self.get_parameter('min_contour_area').value)
        max_area_ratio = float(self.get_parameter('max_contour_area_ratio').value)

        # 1. Recorte da Região de Interesse (ROI) no chão
        y_start = max(0, min(height - 2, int(height * roi_top)))
        y_end = max(y_start + 1, min(height, int(height * roi_bottom)))
        roi = frame[y_start:y_end, :]
        roi_h, roi_w, _ = roi.shape
        roi_total_area = float(roi_h * roi_w)

        blurred = cv2.GaussianBlur(roi, (5, 5), 0)

        # 2. Segmentação da linha
        if mode == 'hsv':
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
            has_contrast = True
        else:
            # Modo dark_line (fita escura em chão claro)
            gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
            min_val, max_val, _, _ = cv2.minMaxLoc(gray)
            contrast = max_val - min_val

            # Se o contraste for insuficiente, o chão é homogêneo (não há linha na visão)
            if contrast < min_contrast:
                mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
                has_contrast = False
            else:
                has_contrast = True
                # Normaliza contraste no range [0..255] para imunidade a sombras
                gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
                thresh = dark_thresh if dark_thresh > 0 else 85
                _, mask = cv2.threshold(gray_norm, thresh, 255, cv2.THRESH_BINARY_INV)

        # 3. Operações morfológicas para eliminar ruídos
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 4. Busca e filtragem de contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        line_found = False
        error_norm = 0.0
        error_px = 0.0
        cx_global = width // 2
        cy_global = (y_start + y_end) // 2
        best_contour = None
        max_allowed_area = roi_total_area * max_area_ratio

        if has_contrast and contours:
            # Filtra apenas contornos com área condizente com uma fita
            valid_contours = []
            for c in contours:
                a = cv2.contourArea(c)
                if min_area <= a <= max_allowed_area:
                    valid_contours.append((c, a))

            if valid_contours:
                # Escolhe o contorno mais expressivo dentro dos limites aceitáveis
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

        # 5. Publicação do erro
        err_msg = Vector3()
        err_msg.x = float(error_norm) if line_found else 0.0
        err_msg.y = float(error_px) if line_found else 0.0
        err_msg.z = 1.0 if line_found else 0.0
        self.error_pub.publish(err_msg)

        # 6. Construção da imagem anotada de Depuração (HUD)
        if self.publish_debug:
            debug_frame = frame.copy()

            # Caixa da ROI (retângulo ciano) e linha central de referência (linha azul vertical)
            box_color = (0, 255, 0) if line_found else (0, 0, 255)
            cv2.rectangle(debug_frame, (0, y_start), (width - 1, y_end - 1), box_color, 2)
            cv2.line(debug_frame, (width // 2, y_start), (width // 2, y_end), (255, 200, 0), 2)

            if line_found and best_contour is not None:
                # Desenha o contorno da linha detectada em verde
                shifted_contour = best_contour + np.array([[[0, y_start]]])
                cv2.drawContours(debug_frame, [shifted_contour], -1, (0, 255, 0), 2)

                # Ponto central da linha (círculo vermelho)
                cv2.circle(debug_frame, (cx_global, cy_global), 8, (0, 0, 255), -1)

                # Vetor de desvio do centro até o alvo (linha amarela horizontal)
                cv2.line(debug_frame, (width // 2, cy_global), (cx_global, cy_global), (0, 255, 255), 3)

                direction_str = "DIREITA" if error_norm > 0.05 else ("ESQUERDA" if error_norm < -0.05 else "CENTRO")
                status_text = f"LINHA OK | Erro: {error_norm:+.2f} ({int(error_px)}px) -> {direction_str}"
                text_color = (0, 255, 0)
            else:
                status_text = "LINHA PERDIDA | Procurando pista..."
                text_color = (0, 0, 255)

            # Barra superior de status (fundo escuro semi-transparente para fácil leitura)
            cv2.rectangle(debug_frame, (0, 0), (width, 42), (0, 0, 0), -1)
            cv2.putText(
                debug_frame, status_text, (15, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, text_color, 2
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
