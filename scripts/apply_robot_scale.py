import os

# 1. Update robot_core.xacro
core_path = 'src/articubot_one/description/robot_core.xacro'
with open(core_path, 'r', encoding='utf-8') as f:
    core = f.read()

replacements_core = [
    ('name="chassis_length" value="0.335"', 'name="chassis_length" value="0.200"'),
    ('name="chassis_width" value="0.265"', 'name="chassis_width" value="0.140"'),
    ('name="chassis_height" value="0.138"', 'name="chassis_height" value="0.080"'),
    ('name="chassis_mass" value="1.0"', 'name="chassis_mass" value="0.6"'),
    ('name="wheel_radius" value="0.033"', 'name="wheel_radius" value="0.025"'),
    ('name="wheel_thickness" value="0.026"', 'name="wheel_thickness" value="0.018"'),
    ('name="wheel_mass" value="0.05"', 'name="wheel_mass" value="0.03"'),
    ('name="wheel_offset_x" value="0.226"', 'name="wheel_offset_x" value="0.135"'),
    ('name="wheel_offset_y" value="0.1485"', 'name="wheel_offset_y" value="0.080"'),
    ('name="wheel_offset_z" value="0.01"', 'name="wheel_offset_z" value="0.005"'),
    ('name="caster_wheel_radius" value="0.01"', 'name="caster_wheel_radius" value="0.008"'),
    ('name="caster_wheel_offset_x" value="0.075"', 'name="caster_wheel_offset_x" value="0.045"'),
]
for old, new in replacements_core:
    core = core.replace(old, new)
with open(core_path, 'w', encoding='utf-8') as f:
    f.write(core)
print('Updated robot_core.xacro')

# 2. Update gazebo_control.xacro
gz_path = 'src/articubot_one/description/gazebo_control.xacro'
with open(gz_path, 'r', encoding='utf-8') as f:
    gz = f.read()
gz = gz.replace('<wheel_separation>0.297</wheel_separation>', '<wheel_separation>0.160</wheel_separation>')
gz = gz.replace('<wheel_diameter>0.066</wheel_diameter>', '<wheel_diameter>0.050</wheel_diameter>')
with open(gz_path, 'w', encoding='utf-8') as f:
    f.write(gz)
print('Updated gazebo_control.xacro')

# 3. Update my_controllers.yaml
ctrl_path = 'src/articubot_one/config/my_controllers.yaml'
with open(ctrl_path, 'r', encoding='utf-8') as f:
    ctrl = f.read()
ctrl = ctrl.replace('wheel_separation: 0.297', 'wheel_separation: 0.160')
ctrl = ctrl.replace('wheel_radius: 0.033', 'wheel_radius: 0.025')
with open(ctrl_path, 'w', encoding='utf-8') as f:
    f.write(ctrl)
print('Updated my_controllers.yaml')

# 4. Update camera.xacro
cam_path = 'src/articubot_one/description/camera.xacro'
with open(cam_path, 'r', encoding='utf-8') as f:
    cam = f.read()
cam = cam.replace('xyz="0.360 0 0.120" rpy="0 0.75 0"', 'xyz="0.210 0 0.090" rpy="0 0.52 0"')
cam = cam.replace('size="0.020 0.040 0.030"', 'size="0.015 0.030 0.020"')
cam = cam.replace('length="0.080"', 'length="0.050"')
with open(cam_path, 'w', encoding='utf-8') as f:
    f.write(cam)
print('Updated camera.xacro')

# 5. Update lidar.xacro
lidar_path = 'src/articubot_one/description/lidar.xacro'
with open(lidar_path, 'r', encoding='utf-8') as f:
    lidar = f.read()
lidar = lidar.replace('xyz="0.122 0 0.212"', 'xyz="0.080 0 0.120"')
lidar = lidar.replace('radius="0.05" length="0.04"', 'radius="0.035" length="0.030"')
lidar = lidar.replace('length="0.1"', 'length="0.05"')
with open(lidar_path, 'w', encoding='utf-8') as f:
    f.write(lidar)
print('Updated lidar.xacro')

# 6. Update face.xacro
face_path = 'src/articubot_one/description/face.xacro'
with open(face_path, 'r', encoding='utf-8') as f:
    face = f.read()
face = face.replace('radius="0.01" length="0.002"', 'radius="0.006" length="0.002"')
face = face.replace('radius="0.05" length="0.02"', 'radius="0.025" length="0.010"')
face = face.replace('origin xyz="0 0.05 0.01"', 'origin xyz="0 0.03 0.008"')
face = face.replace('origin xyz="0 -0.05 0.01"', 'origin xyz="0 -0.03 0.008"')
with open(face_path, 'w', encoding='utf-8') as f:
    f.write(face)
print('Updated face.xacro')

# 7. Update line_detector_node.py
ld_path = 'src/agv_brain/agv_brain/line_detector_node.py'
with open(ld_path, 'r', encoding='utf-8') as f:
    ld = f.read()
ld = ld.replace("self.declare_parameter('max_contour_area_ratio', 0.45)", "self.declare_parameter('max_contour_area_ratio', 0.85)")
ld = ld.replace("self.declare_parameter('min_contour_area', 100.0)", "self.declare_parameter('min_contour_area', 50.0)")
ld = ld.replace("self.declare_parameter('min_contrast', 25.0)", "self.declare_parameter('min_contrast', 20.0)")
ld = ld.replace("self.declare_parameter('dark_threshold', 85)", "self.declare_parameter('dark_threshold', 95)")
with open(ld_path, 'w', encoding='utf-8') as f:
    f.write(ld)
print('Updated line_detector_node.py')

# 8. Update auto_start defaults in launch files
for path in ['src/agv_hardware/launch/agv_complete.launch.py', 'src/agv_brain/launch/brain.launch.py']:
    with open(path, 'r', encoding='utf-8') as f:
        t = f.read()
    t = t.replace("default_value='false',\n            description='Se true, inicia seguindo linha", "default_value='true',\n            description='Se true, inicia seguindo linha")
    t = t.replace("default_value='false',\r\n            description='Se true, inicia seguindo linha", "default_value='true',\r\n            description='Se true, inicia seguindo linha")
    t = t.replace("default_value='false',\n            description='Se true, comeca a seguir linha", "default_value='true',\n            description='Se true, comeca a seguir linha")
    t = t.replace("default_value='false',\r\n            description='Se true, comeca a seguir linha", "default_value='true',\r\n            description='Se true, comeca a seguir linha")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(t)
    print('Updated auto_start in', path)
