import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_name = 'articubot_one'
    pkg_share = get_package_share_directory(pkg_name)

    default_rviz_config = os.path.join(pkg_share, 'config', 'sim_robot.rviz')
    if not os.path.isfile(default_rviz_config):
        default_rviz_config = os.path.join(pkg_share, 'config', 'view_bot.rviz')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_gui_wheels = LaunchConfiguration('use_gui_wheels')
    launch_rsp = LaunchConfiguration('launch_rsp')
    rviz_config = LaunchConfiguration('rviz_config')

    # Argumentos configuráveis
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Usa o tempo simulado do Gazebo (/clock)'
    )

    declare_use_gui_wheels = DeclareLaunchArgument(
        'use_gui_wheels',
        default_value='false',
        description='Ativa sliders manuais de rodas (somente para teste offline sem simulacao)'
    )

    declare_launch_rsp = DeclareLaunchArgument(
        'launch_rsp',
        default_value='false',
        description='Inicia robot_state_publisher (deve ser false se a simulacao ja estiver ativa)'
    )

    declare_rviz_config = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_config,
        description='Caminho completo para o arquivo .rviz de visualizacao'
    )

    # 1. Carrega o Robot State Publisher (somente se launch_rsp:=true, para testes offline)
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'rsp.launch.py')
        ]),
        launch_arguments={'use_sim_time': use_sim_time, 'use_ros2_control': 'false'}.items(),
        condition=IfCondition(launch_rsp),
    )

    # 2. Sliders manuais de juntas (somente se use_gui_wheels:=true, para nao travar as rodas do Gazebo)
    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        condition=IfCondition(use_gui_wheels),
    )

    # 3. Abre o RViz 2 sincronizado com o Gazebo (Fixed Frame odom, Lidar e Odometria)
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_use_gui_wheels,
        declare_launch_rsp,
        declare_rviz_config,
        rsp,
        joint_state_publisher_gui,
        rviz2_node,
    ])
