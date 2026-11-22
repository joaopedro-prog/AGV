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
    enable_lidar = LaunchConfiguration('enable_lidar')
    lidar_port = LaunchConfiguration('lidar_port')

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

    # 2. Twist Mux (Gerencia prioridades: Emergência 255 > Joystick 100 > Linha 30 > Nav2 10)
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        output='screen',
        parameters=[twist_mux_params, {'use_sim_time': False}],
        remappings=[('/cmd_vel_out', '/diff_cont/cmd_vel_unstamped')],
    )

    # 3. Ponte Serial com o ESP32 (REV Spark MAX PWM, Encoders KY-040 e 2x HC-SR04)
    serial_bridge = Node(
        package='agv_hardware',
        executable='serial_bridge',
        name='serial_bridge',
        output='screen',
        parameters=[hw_params_file, {'use_sim_time': False}],
    )

    # 4. GPIO RPi (Relés K1 Ventoinhas / K2 Fita LED) e IMU MPU6050 I2C
    rpi_sensors = Node(
        package='agv_hardware',
        executable='rpi_sensors',
        name='rpi_sensors',
        output='screen',
        parameters=[hw_params_file, {'use_sim_time': False}],
    )

    # 5. Câmera CSI / USB Real (v4l2_camera publicando 320x240 @ 15fps em /camera/image_raw)
    camera_node = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='v4l2_camera',
        namespace='camera',
        output='screen',
        parameters=[hw_params_file, {'use_sim_time': False}],
        condition=IfCondition(enable_camera),
    )

    # 6. Sensor LiDAR 360° RPLIDAR A1 (condicional a enable_lidar)
    lidar_node = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        name='rplidar_composition',
        output='screen',
        parameters=[
            hw_params_file,
            {
                'use_sim_time': False,
                'serial_port': lidar_port,
            },
        ],
        condition=IfCondition(enable_lidar),
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
            description='Inicia o driver da camera CSI/USB real (v4l2_camera)',
        ),
        DeclareLaunchArgument(
            'enable_lidar',
            default_value='true',
            description='Se true, inicia o driver rplidar_ros no robo fisico',
        ),
        DeclareLaunchArgument(
            'lidar_port',
            default_value='/dev/agv_lidar',
            description='Porta serial do RPLIDAR A1 (ex: /dev/agv_lidar ou /dev/ttyUSB1)',
        ),
        rsp,
        twist_mux,
        serial_bridge,
        rpi_sensors,
        camera_node,
        lidar_node,
    ])
