import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    port = LaunchConfiguration('port')
    host = LaunchConfiguration('host')

    web_dashboard_node = Node(
        package='agv_brain',
        executable='web_dashboard',
        name='web_dashboard',
        output='screen',
        parameters=[{
            'port': port,
            'host': host,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='5000',
            description='Porta do servidor HTTP do Dashboard Web (padrao: 5000)',
        ),
        DeclareLaunchArgument(
            'host',
            default_value='0.0.0.0',
            description='Endereco de bind da rede (padrao: 0.0.0.0)',
        ),
        web_dashboard_node,
    ])
