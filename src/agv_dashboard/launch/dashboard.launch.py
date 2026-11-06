import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    port_arg = DeclareLaunchArgument(
        'web_port',
        default_value='8080',
        description='Porta HTTP do Dashboard Web do AGV'
    )

    dashboard_node = Node(
        package='agv_dashboard',
        executable='dashboard_server',
        name='dashboard_server',
        output='screen',
        parameters=[{
            'web_port': LaunchConfiguration('web_port')
        }]
    )

    return LaunchDescription([
        port_arg,
        dashboard_node
    ])
