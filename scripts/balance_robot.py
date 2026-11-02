path = 'src/articubot_one/description/robot_core.xacro'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Center the drive wheels along the chassis length
text = text.replace('name="wheel_offset_x" value="0.135"', 'name="wheel_offset_x" value="0.100"')

# 2. Add low friction to chassis just in case
old_chassis_gz = """    <gazebo reference="chassis">
        <material>Gazebo/Orange</material>
    </gazebo>"""

new_chassis_gz = """    <gazebo reference="chassis">
        <material>Gazebo/Orange</material>
        <mu1 value="0.001"/>
        <mu2 value="0.001"/>
    </gazebo>"""
text = text.replace(old_chassis_gz, new_chassis_gz)

# 3. Two caster wheels (front and rear) for 100% stable balance
old_caster_block = """    <!-- CASTER WHEEL LINK -->

    <joint name="caster_wheel_joint" type="fixed">
        <parent link="chassis"/>
        <child link="caster_wheel"/>
        <origin xyz="${caster_wheel_offset_x} 0 ${caster_wheel_offset_z}"/>
    </joint>


    <link name="caster_wheel">
        <visual>
            <geometry>
                <sphere radius="${caster_wheel_radius}"/>
            </geometry>
            <material name="white"/>
        </visual>
        <collision>
            <geometry>
                <sphere radius="${caster_wheel_radius}"/>
            </geometry>
        </collision>
        <xacro:inertial_sphere mass="${caster_wheel_mass}" radius="${caster_wheel_radius}">
            <origin xyz="0 0 0" rpy="0 0 0"/>
        </xacro:inertial_sphere>
    </link>

    <gazebo reference="caster_wheel">
        <material>Gazebo/White</material>
        <mu1 value="0.001"/>
        <mu2 value="0.001"/>
    </gazebo>"""

new_caster_block = """    <!-- FRONT CASTER WHEEL LINK -->

    <joint name="front_caster_wheel_joint" type="fixed">
        <parent link="chassis"/>
        <child link="front_caster_wheel"/>
        <origin xyz="0.170 0 ${caster_wheel_offset_z}"/>
    </joint>

    <link name="front_caster_wheel">
        <visual>
            <geometry>
                <sphere radius="${caster_wheel_radius}"/>
            </geometry>
            <material name="white"/>
        </visual>
        <collision>
            <geometry>
                <sphere radius="${caster_wheel_radius}"/>
            </geometry>
        </collision>
        <xacro:inertial_sphere mass="${caster_wheel_mass}" radius="${caster_wheel_radius}">
            <origin xyz="0 0 0" rpy="0 0 0"/>
        </xacro:inertial_sphere>
    </link>

    <gazebo reference="front_caster_wheel">
        <material>Gazebo/White</material>
        <mu1 value="0.001"/>
        <mu2 value="0.001"/>
    </gazebo>

    <!-- REAR CASTER WHEEL LINK -->

    <joint name="rear_caster_wheel_joint" type="fixed">
        <parent link="chassis"/>
        <child link="rear_caster_wheel"/>
        <origin xyz="0.030 0 ${caster_wheel_offset_z}"/>
    </joint>

    <link name="rear_caster_wheel">
        <visual>
            <geometry>
                <sphere radius="${caster_wheel_radius}"/>
            </geometry>
            <material name="white"/>
        </visual>
        <collision>
            <geometry>
                <sphere radius="${caster_wheel_radius}"/>
            </geometry>
        </collision>
        <xacro:inertial_sphere mass="${caster_wheel_mass}" radius="${caster_wheel_radius}">
            <origin xyz="0 0 0" rpy="0 0 0"/>
        </xacro:inertial_sphere>
    </link>

    <gazebo reference="rear_caster_wheel">
        <material>Gazebo/White</material>
        <mu1 value="0.001"/>
        <mu2 value="0.001"/>
    </gazebo>"""

text = text.replace(old_caster_block, new_caster_block)
with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated dual caster balance in robot_core.xacro!')
