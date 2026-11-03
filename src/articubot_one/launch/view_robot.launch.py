import os
import subprocess

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    pkg_name = 'articubot_one'
    pkg_share = get_package_share_directory(pkg_name)

    # 1. Verifica se Gazebo está ativo no sistema
    is_gazebo_running = False
    try:
        res = subprocess.run(['pgrep', '-x', 'gzserver'], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            is_gazebo_running = True
    except Exception:
        pass

    use_sim_time_arg = LaunchConfiguration('use_sim_time').perform(context).strip().lower()
    if use_sim_time_arg in ('auto', ''):
        use_sim_time_val = is_gazebo_running
    else:
        use_sim_time_val = (use_sim_time_arg in ('true', '1'))

    custom_rviz_arg = LaunchConfiguration('rviz_config').perform(context).strip()

    # 2. Escolhe a configuração de RViz apropriada
    if custom_rviz_arg and os.path.isfile(custom_rviz_arg):
        rviz_file = custom_rviz_arg
    elif is_gazebo_running and use_sim_time_val:
        rviz_file = os.path.join(pkg_share, 'config', 'sim_robot.rviz')
        print("[view_robot] Gazebo ativo detectado: sincronizando RViz com /odom e tempo de simulacao (/clock)...")
    else:
        rviz_file = os.path.join(pkg_share, 'config', 'view_bot.rviz')
        print("[view_robot] Modo visualizacao direta do modelo CAD (Fixed Frame: base_link, tempo real)...")

    actions = []

    # 3. Se Gazebo NÃO estiver rodando, inicia o Robot State Publisher e Joint State Publisher
    # para que o modelo 3D real e todas as juntas sejam renderizadas perfeitamente no RViz!
    if not is_gazebo_running:
        rsp = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                os.path.join(pkg_share, 'launch', 'rsp.launch.py')
            ]),
            launch_arguments={'use_sim_time': 'false', 'use_ros2_control': 'false'}.items(),
        )
        actions.append(rsp)

        jsp = Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            parameters=[{'use_sim_time': False}],
        )
        actions.append(jsp)

    # 4. Inicia o nó do RViz 2
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': use_sim_time_val}],
    )
    actions.append(rviz2_node)

    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='auto',
            description='auto detecta se Gazebo esta rodando, ou defina true/false'
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value='',
            description='Caminho customizado para arquivo .rviz'
        ),
        OpaqueFunction(function=launch_setup),
    ])
