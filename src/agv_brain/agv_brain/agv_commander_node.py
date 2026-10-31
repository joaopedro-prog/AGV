#!/usr/bin/env python3
"""
Utilitário de Comando do AGV (CLI e Painel Interativo).

Uso rápido via linha de comando:
  ros2 run agv_brain agv_cmd start
  ros2 run agv_brain agv_cmd stop

Ou modo interativo (menu no terminal):
  ros2 run agv_brain agv_cmd
"""

import sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import SetBool


class AgvCommanderNode(Node):
    def __init__(self):
        super().__init__('agv_commander')
        self.cmd_pub = self.create_publisher(String, '/agv/command', 10)
        self.srv_client = self.create_client(SetBool, '/agv/set_following')

    def send_command(self, enable: bool):
        """Envia comando tanto pelo Serviço quanto pelo Tópico para máxima confiabilidade."""
        msg = String()
        msg.data = 'START' if enable else 'STOP'
        self.cmd_pub.publish(msg)

        if self.srv_client.wait_for_service(timeout_sec=1.0):
            req = SetBool.Request()
            req.data = enable
            future = self.srv_client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
            if future.result() is not None:
                self.get_logger().info(f'Resposta do AGV: {future.result().message}')
                return
        self.get_logger().info(f'Comando [{msg.data}] publicado em /agv/command!')


def main(args=None):
    rclpy.init(args=args)
    node = AgvCommanderNode()

    cli_args = [a.lower() for a in sys.argv[1:] if not a.startswith('-')]
    if cli_args:
        action = cli_args[0]
        if action in ('start', 'go', 'on', '1'):
            node.send_command(True)
        elif action in ('stop', 'idle', 'off', '0'):
            node.send_command(False)
        else:
            print('Uso: ros2 run agv_brain agv_cmd [start|stop]')
        node.destroy_node()
        rclpy.shutdown()
        return

    # Menu interativo no terminal
    try:
        while rclpy.ok():
            print('\n============================================')
            print('       PAINEL DE COMANDO DO AGV (ROS 2)     ')
            print('============================================')
            print('  [1] INICIAR Seguidor de Linha (START)')
            print('  [2] PARAR Robô Imediatamente  (STOP)')
            print('  [q] Sair do painel')
            print('============================================')
            choice = input('Escolha uma opção: ').strip().lower()
            if choice in ('1', 'start', 's'):
                node.send_command(True)
            elif choice in ('2', 'stop', 'p'):
                node.send_command(False)
            elif choice in ('q', 'quit', 'exit'):
                break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
