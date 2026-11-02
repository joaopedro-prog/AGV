# 1. Update camera.xacro to remove colons in comments
path_cam = 'src/articubot_one/description/camera.xacro'
with open(path_cam, 'r', encoding='utf-8') as f:
    cam = f.read()

# Replace colons in comments
cam = cam.replace('Arquivo:', 'Arquivo -')
cam = cam.replace('Joint:', 'Joint -')
cam = cam.replace('PADRÃO ATUAL:', 'PADRÃO ATUAL -')
cam = cam.replace('POSIÇÃO (xyz em metros):', 'POSIÇÃO (xyz em metros) -')
with open(path_cam, 'w', encoding='utf-8') as f:
    cam_written = f.write(cam)
print('Updated camera.xacro')

# 2. Update launch_robot.launch.py
path_lr = 'src/articubot_one/launch/launch_robot.launch.py'
with open(path_lr, 'r', encoding='utf-8') as f:
    lr = f.read()

if 'ParameterValue' not in lr:
    lr = lr.replace(
        'from launch.actions import IncludeLaunchDescription, TimerAction',
        'from launch.actions import IncludeLaunchDescription, TimerAction\nfrom launch_ros.parameter_descriptions import ParameterValue'
    )
    lr = lr.replace(
        "Command(['ros2 param get --hide-type /robot_state_publisher robot_description'])",
        "ParameterValue(Command(['ros2 param get --hide-type /robot_state_publisher robot_description']), value_type=str)"
    )
    with open(path_lr, 'w', encoding='utf-8') as f:
        f.write(lr)
    print('Updated launch_robot.launch.py')
