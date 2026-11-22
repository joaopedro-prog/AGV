"""
Launch Orquestrador Mestre do AGV (Simulação vs Robô Real).

Como usar:
  1) MODO SIMULAÇÃO (Gazebo + Visão + Seguidor de Linha):
     ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true world:=armazem_logistico.world

  2) MODO ROBÔ REAL NA RASPBERRY PI 3B (ESP32 + Câmera + Visão + Dashboard):
     ros2 launch agv_hardware agv_complete.launch.py sim_mode:=false
     (Opcional com LiDAR conectado): enable_lidar:=true lidar_port:=/dev/agv_lidar
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression


def generate_launch_description():
    pkg_desc = get_package_share_directory('articubot_one')
    pkg_hw = get_package_share_directory('agv_hardware')
    pkg_brain = get_package_share_directory('agv_brain')
    pkg_dash = get_package_share_directory('agv_dashboard')

    sim_mode = LaunchConfiguration('sim_mode')
    auto_start = LaunchConfiguration('auto_start')
    enable_camera = LaunchConfiguration('enable_camera')
    enable_lidar = LaunchConfiguration('enable_lidar')
    lidar_port = LaunchConfiguration('lidar_port')
    enable_dashboard = LaunchConfiguration('enable_dashboard')
    web_port = LaunchConfiguration('web_port')
    world = LaunchConfiguration('world')

    # A) Camada de Simulação (executada somente quando sim_mode == true)
    sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_desc, 'launch', 'launch_sim.launch.py')
        ]),
        launch_arguments={'world': world}.items(),
        condition=IfCondition(sim_mode),
    )

    # B) Camada de Hardware Real (executada somente quando sim_mode == false)
    real_hw_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_hw, 'launch', 'hardware_bringup.launch.py')
        ]),
        launch_arguments={
            'enable_camera': enable_camera,
            'enable_lidar': enable_lidar,
            'lidar_port': lidar_port,
        }.items(),
        condition=UnlessCondition(sim_mode),
    )

    # C) Camada de Inteligência (Visão OpenCV + Controle PID - roda em AMBOS os modos!)
    brain_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_brain, 'launch', 'brain.launch.py')
        ]),
        launch_arguments={
            'use_sim_time': sim_mode,
            'auto_start': auto_start,
        }.items(),
    )

    # D) Dashboard Web HMI (inicia automaticamente no modo robô real quando enable_dashboard:=true)
    dashboard_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_dash, 'launch', 'dashboard.launch.py')
        ]),
        launch_arguments={'web_port': web_port}.items(),
        condition=IfCondition(
            PythonExpression([
                "'", sim_mode, "'.lower() == 'false' and '",
                enable_dashboard, "'.lower() == 'true'"
            ])
        ),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'sim_mode',
            default_value='true',
            description='True para rodar no Gazebo (PC), False para rodar no Robo Real (Raspberry Pi)',
        ),
        DeclareLaunchArgument(
            'world',
            default_value='pista_completa_plana.world',
            description='Nome do mundo do Gazebo (armazem_logistico.world, pista_completa_plana.world, etc)',
        ),
        DeclareLaunchArgument(
            'auto_start',
            default_value='false',
            description='Se true, inicia seguindo linha automaticamente. Se false, aguarda seu comando START.',
        ),
        DeclareLaunchArgument(
            'enable_camera',
            default_value='true',
            description='No modo real (sim_mode:=false), ativa a camera CSI/USB v4l2_camera',
        ),
        DeclareLaunchArgument(
            'enable_lidar',
            default_value='false',
            description='Desativado por padrao: modelo fisico usa 2x HC-SR04 frontais sem LiDAR',
        ),
        DeclareLaunchArgument(
            'lidar_port',
            default_value='/dev/agv_lidar',
            description='Porta serial do RPLIDAR A1 no robo real',
        ),
        DeclareLaunchArgument(
            'enable_dashboard',
            default_value='true',
            description='Se true no modo robo real (sim_mode:=false), sobe automaticamente o Dashboard Web',
        ),
        DeclareLaunchArgument(
            'web_port',
            default_value='8080',
            description='Porta HTTP do Dashboard Web do AGV',
        ),
        sim_launch,
        real_hw_launch,
        brain_launch,
        dashboard_launch,
    ])
