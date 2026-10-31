import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_name = 'articubot_one'
    pkg_share = get_package_share_directory(pkg_name)

    rviz_config_file = os.path.join(pkg_share, 'config', 'view_bot.rviz')

    # 1. Carrega o Robot State Publisher (processa o Xacro do robô)
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'rsp.launch.py')
        ]),
        launch_arguments={'use_sim_time': 'false', 'use_ros2_control': 'false'}.items(),
    )

    # 2. Interface gráfica para mover as juntas/rodas no RViz com sliders
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
    )

    # 3. Abre o RViz 2 com a configuração visual pré-definida
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
    )

    return LaunchDescription([
        rsp,
        joint_state_publisher_gui,
        rviz2_node,
    ])
