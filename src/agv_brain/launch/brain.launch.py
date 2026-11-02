import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_brain = get_package_share_directory('agv_brain')
    default_params_file = os.path.join(pkg_brain, 'config', 'brain_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time')
    auto_start = LaunchConfiguration('auto_start')
    params_file = LaunchConfiguration('params_file')

    line_detector_node = Node(
        package='agv_brain',
        executable='line_detector',
        name='line_detector',
        output='screen',
        parameters=[
            params_file,
            {'use_sim_time': use_sim_time},
        ],
    )

    line_follower_node = Node(
        package='agv_brain',
        executable='line_follower',
        name='line_follower',
        output='screen',
        parameters=[
            params_file,
            {
                'use_sim_time': use_sim_time,
                'auto_start': auto_start,
            },
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='True quando rodando no Gazebo, False na Raspberry Pi real',
        ),
        DeclareLaunchArgument(
            'auto_start',
            default_value='true',
            description='Se true, comeca a seguir linha imediatamente sem aguardar comando START',
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params_file,
            description='Caminho para o arquivo brain_params.yaml',
        ),
        line_detector_node,
        line_follower_node,
    ])
