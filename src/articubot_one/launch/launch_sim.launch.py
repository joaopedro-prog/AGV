import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_name = 'articubot_one'
    pkg_share = get_package_share_directory(package_name)

    default_world = os.path.join(pkg_share, 'worlds', 'circuit1.world')
    world = LaunchConfiguration('world')
    spawn_x = LaunchConfiguration('spawn_x')
    spawn_y = LaunchConfiguration('spawn_y')
    spawn_z = LaunchConfiguration('spawn_z')
    spawn_yaw = LaunchConfiguration('spawn_yaw')
    use_ros2_control = LaunchConfiguration('use_ros2_control')

    # 1. Robot State Publisher (Geometria URDF do robô)
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(pkg_share, 'launch', 'rsp.launch.py')
        ]),
        launch_arguments={
            'use_sim_time': 'true',
            'use_ros2_control': use_ros2_control,
        }.items(),
    )

    # 2. Twist Mux (prioridade de comandos: Joystick > Seguidor de Linha > Nav2)
    twist_mux_params = os.path.join(pkg_share, 'config', 'twist_mux.yaml')
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[twist_mux_params, {'use_sim_time': True}],
        remappings=[('/cmd_vel_out', '/cmd_vel')],
    )

    # 3. Gazebo Classic com parâmetros e mundo da pista
    gazebo_params_file = os.path.join(pkg_share, 'config', 'gazebo_params.yaml')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ]),
        launch_arguments={
            'world': world,
            'extra_gazebo_args': '--ros-args --params-file ' + gazebo_params_file,
        }.items(),
    )

    # 4. Spawna o robô no Gazebo
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'my_bot',
            '-x', spawn_x,
            '-y', spawn_y,
            '-z', spawn_z,
            '-Y', spawn_yaw,
        ],
        output='screen',
    )

    # 5. Spawners opcionais se use_ros2_control:=true
    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_cont'],
        condition=IfCondition(use_ros2_control),
    )

    joint_broad_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_broad'],
        condition=IfCondition(use_ros2_control),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value=default_world,
            description='Mundo do Gazebo a ser carregado (padrao: circuit1.world)',
        ),
        DeclareLaunchArgument(
            'use_ros2_control',
            default_value='false',
            description='False usa o driver nativo estavel diff_drive do Gazebo',
        ),
        DeclareLaunchArgument('spawn_x', default_value='0.05'),
        DeclareLaunchArgument('spawn_y', default_value='-0.157'),
        DeclareLaunchArgument('spawn_z', default_value='0.035'),
        DeclareLaunchArgument('spawn_yaw', default_value='0.0'),
        rsp,
        twist_mux,
        gazebo,
        spawn_entity,
        diff_drive_spawner,
        joint_broad_spawner,
    ])
