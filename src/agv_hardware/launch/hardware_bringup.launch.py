import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_desc = get_package_share_directory('articubot_one')
    pkg_hw = get_package_share_directory('agv_hardware')

    hw_params_file = LaunchConfiguration('hw_params_file')
    enable_camera = LaunchConfiguration('enable_camera')

    default_hw_params = os.path.join(pkg_hw, 'config', 'hardware_params.yaml')
    twist_mux_params = os.path.join(pkg_desc, 'config', 'twist_mux.yaml')

    # 1. Robot State Publisher (Geometria URDF do Robô, use_sim_time=false)
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_desc, 'launch', 'rsp.launch.py')
        ]),
        launch_arguments={
            'use_sim_time': 'false',
            'use_ros2_control': 'false',
        }.items(),
    )

    # 2. Twist Mux (Gerencia prioridades entre Joystick, Seguidor de Linha e Nav2)
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        output='screen',
        parameters=[twist_mux_params, {'use_sim_time': False}],
        remappings=[('/cmd_vel_out', '/diff_cont/cmd_vel_unstamped')],
    )

    # 3. Ponte Serial com o Microcontrolador (Motores, Encoders e Sensores Seriais)
    serial_bridge = Node(
        package='agv_hardware',
        executable='serial_bridge',
        name='serial_bridge',
        output='screen',
        parameters=[hw_params_file, {'use_sim_time': False}],
    )

    # 4. Sensores e Botões Físicos ligados direto na Raspberry Pi (GPIO)
    rpi_sensors = Node(
        package='agv_hardware',
        executable='rpi_sensors',
        name='rpi_sensors',
        output='screen',
        parameters=[hw_params_file, {'use_sim_time': False}],
    )

    # 5. Câmera USB Real (v4l2_camera publicando em /camera/image_raw)
    camera_node = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='v4l2_camera',
        namespace='camera',
        output='screen',
        parameters=[hw_params_file, {'use_sim_time': False}],
        condition=IfCondition(enable_camera),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'hw_params_file',
            default_value=default_hw_params,
            description='Arquivo YAML com portas e constantes fisicas do robo real',
        ),
        DeclareLaunchArgument(
            'enable_camera',
            default_value='true',
            description='Inicia o driver da camera USB real (v4l2_camera)',
        ),
        rsp,
        twist_mux,
        serial_bridge,
        rpi_sensors,
        camera_node,
    ])
