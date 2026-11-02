"""
Launch Orquestrador Mestre do AGV (Simulação vs Robô Real).

Como usar:
  1) MODO SIMULAÇÃO (Gazebo + Visão + Seguidor de Linha):
     ros2 launch agv_hardware agv_complete.launch.py sim_mode:=true world:=circuit1.world

  2) MODO ROBÔ REAL NA RASPBERRY PI (Serial MCU + Câmera USB + Visão + Seguidor de Linha):
     ros2 launch agv_hardware agv_complete.launch.py sim_mode:=false
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_desc = get_package_share_directory('articubot_one')
    pkg_hw = get_package_share_directory('agv_hardware')
    pkg_brain = get_package_share_directory('agv_brain')

    sim_mode = LaunchConfiguration('sim_mode')
    auto_start = LaunchConfiguration('auto_start')
    enable_camera = LaunchConfiguration('enable_camera')
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
        launch_arguments={'enable_camera': enable_camera}.items(),
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

    return LaunchDescription([
        DeclareLaunchArgument(
            'sim_mode',
            default_value='true',
            description='True para rodar no Gazebo (PC), False para rodar no Robo Real (Raspberry Pi)',
        ),
        DeclareLaunchArgument(
            'world',
            default_value='pista_completa_3d.world',
            description='Nome ou caminho do mundo do Gazebo (ex: circuit1.world, circle_world.world, empty.world)',
        ),
        DeclareLaunchArgument(
            'auto_start',
            default_value='false',
            description='Se true, inicia seguindo linha automaticamente. Se false, aguarda seu comando START.',
        ),
        DeclareLaunchArgument(
            'enable_camera',
            default_value='true',
            description='No modo real (sim_mode:=false), ativa a camera USB v4l2_camera',
        ),
        sim_launch,
        real_hw_launch,
        brain_launch,
    ])
