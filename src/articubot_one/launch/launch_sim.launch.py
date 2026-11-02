import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    package_name = 'articubot_one'
    pkg_share = get_package_share_directory(package_name)

    world_arg = LaunchConfiguration('world').perform(context).strip()
    use_ros2_control = LaunchConfiguration('use_ros2_control')
    spawn_x_val = LaunchConfiguration('spawn_x').perform(context)
    spawn_y_val = LaunchConfiguration('spawn_y').perform(context)
    spawn_z_val = LaunchConfiguration('spawn_z').perform(context)
    spawn_yaw_val = LaunchConfiguration('spawn_yaw').perform(context)
    gazebo_params_file = os.path.join(pkg_share, 'config', 'gazebo_params.yaml')

    # Busca abrangente do arquivo de mundo (priorizando arquivos editados em src e worlds)
    candidates = [
        world_arg,
        world_arg + ('' if world_arg.endswith('.world') else '.world'),
        os.path.join('/workspace/src/articubot_one/worlds', world_arg),
        os.path.join('/workspace/src/articubot_one/worlds', world_arg + ('' if world_arg.endswith('.world') else '.world')),
        os.path.join('/workspace/worlds', world_arg),
        os.path.join('/workspace/worlds', world_arg + ('' if world_arg.endswith('.world') else '.world')),
        os.path.join(pkg_share, 'worlds', world_arg),
        os.path.join(pkg_share, 'worlds', world_arg + ('' if world_arg.endswith('.world') else '.world')),
        os.path.join('/workspace/gazebo_world', world_arg),
        os.path.join('/workspace/gazebo_world', world_arg + ('' if world_arg.endswith('.world') else '.world')),
    ]

    resolved_world = None
    for path in candidates:
        if os.path.isfile(path):
            resolved_world = os.path.abspath(path)
            break

    if not resolved_world:
        default_world = os.path.join('/workspace/src/articubot_one/worlds', 'circuit1.world')
        if not os.path.isfile(default_world):
            default_world = os.path.join(pkg_share, 'worlds', 'circuit1.world')
        resolved_world = default_world
        print(f"[launch_sim] AVISO: Mundo '{world_arg}' nao encontrado. Usando padrao: {resolved_world}")
    else:
        print(f"[launch_sim] Carregando mundo no Gazebo: {resolved_world}")

    # Ajusta o spawn padrão sobre a linha conforme o mundo se não houver coordenadas customizadas
    if 'circle' in resolved_world.lower() and spawn_x_val == '0.05' and spawn_y_val == '-0.157':
        spawn_x_val = '0.0'
        spawn_y_val = '0.30'
        spawn_z_val = '0.05'
        spawn_yaw_val = '0.0'
        print(f"[launch_sim] Posição de spawn ajustada para circle_world: x={spawn_x_val}, y={spawn_y_val}")

    # Gazebo Classic com parâmetros e mundo da pista
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ]),
        launch_arguments={
            'world': resolved_world,
            'extra_gazebo_args': '--ros-args --params-file ' + gazebo_params_file,
        }.items(),
    )

    # Spawna o robô no Gazebo
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'my_bot',
            '-x', spawn_x_val,
            '-y', spawn_y_val,
            '-z', spawn_z_val,
            '-Y', spawn_yaw_val,
            '-timeout', '120.0',
            '-spawn_service_timeout', '120.0',
        ],
        output='screen',
    )

    # Spawners opcionais se use_ros2_control:=true
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

    return [
        gazebo,
        spawn_entity,
        diff_drive_spawner,
        joint_broad_spawner,
    ]


def generate_launch_description():
    package_name = 'articubot_one'
    pkg_share = get_package_share_directory(package_name)

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

    return LaunchDescription([
        DeclareLaunchArgument(
            'world',
            default_value='circuit1.world',
            description='Mundo do Gazebo a ser carregado (ex: circuit1.world, circle_world.world, empty.world)',
        ),
        DeclareLaunchArgument(
            'use_ros2_control',
            default_value='false',
            description='False usa o driver nativo estavel diff_drive do Gazebo',
        ),
        DeclareLaunchArgument('spawn_x', default_value='0.05'),
        DeclareLaunchArgument('spawn_y', default_value='-0.157'),
        DeclareLaunchArgument('spawn_z', default_value='0.05'),
        DeclareLaunchArgument('spawn_yaw', default_value='0.0'),
        rsp,
        twist_mux,
        OpaqueFunction(function=launch_setup),
    ])
