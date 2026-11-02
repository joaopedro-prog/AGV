import os
import xml.etree.ElementTree as ET

# Poses for the 8-tile stadium loop (90x90cm)
tiles = [
    # (name, folder, mesh_file, x, y, z, r, p, yaw)
    ('tile_reta_top', 'tile-reta', 'tile_reta.dae', -0.15, 0.45, 0.001, 0, 0, 0.0),
    ('tile_curva_tr', 'tile-curva', 'tile_curva.dae', 0.15, 0.45, 0.001, 0, 0, 0.0),
    ('tile_reta_right', 'tile-reta', 'tile_reta.dae', 0.45, 0.15, 0.001, 0, 0, -1.570796),
    ('tile_curva_br', 'tile-curva', 'tile_curva.dae', 0.45, -0.15, 0.001, 0, 0, -1.570796),
    ('tile_reta_bottom', 'tile-reta', 'tile_reta.dae', 0.15, -0.45, 0.001, 0, 0, 3.141593),
    ('tile_curva_bl', 'tile-curva', 'tile_curva.dae', -0.15, -0.45, 0.001, 0, 0, 3.141593),
    ('tile_reta_left', 'tile-reta', 'tile_reta.dae', -0.45, -0.15, 0.001, 0, 0, 1.570796),
    ('tile_curva_tl', 'tile-curva', 'tile_curva.dae', -0.45, 0.15, 0.001, 0, 0, 1.570796),
]

models_xml = []
for name, folder, mesh_file, x, y, z, r, p, yaw in tiles:
    xml = f"""    <model name='{name}'>
      <static>1</static>
      <link name='link'>
        <visual name='visual'>
          <pose>0 0 0 1.5708 -0 0</pose>
          <geometry>
            <mesh>
              <uri>/workspace/tiles/{folder}/meshes/{mesh_file}</uri>
              <scale>1 1 1</scale>
            </mesh>
          </geometry>
        </visual>
        <collision name='collision'>
          <geometry>
            <box>
              <size>0.30 0.30 0.003</size>
            </box>
          </geometry>
          <max_contacts>10</max_contacts>
          <surface>
            <contact><ode/></contact>
            <bounce/>
            <friction>
              <torsional><ode/></torsional>
              <ode/>
            </friction>
          </surface>
        </collision>
        <self_collide>0</self_collide>
        <enable_wind>0</enable_wind>
        <kinematic>0</kinematic>
      </link>
      <pose>{x:.4f} {y:.4f} {z:.4f} {r} {p} {yaw:.6f}</pose>
    </model>"""
    models_xml.append(xml)

tiles_str = "\n\n".join(models_xml)

world_content = f"""<sdf version='1.7'>
  <world name='default'>
    <light name='sun' type='directional'>
      <cast_shadows>0</cast_shadows>
      <pose>0 0 5 0 -0 0</pose>
      <diffuse>1 1 1 1</diffuse>
      <specular>0.3 0.3 0.3 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>0 0 -1</direction>
    </light>
    <light name='overhead_light' type='point'>
      <cast_shadows>0</cast_shadows>
      <pose>0 0 2.5 0 0 0</pose>
      <diffuse>1 1 1 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation>
        <range>20</range>
        <constant>0.5</constant>
        <linear>0.05</linear>
        <quadratic>0.005</quadratic>
      </attenuation>
    </light>
    <model name='ground_plane'>
      <static>1</static>
      <link name='link'>
        <collision name='collision'>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
          <surface>
            <contact>
              <collide_bitmask>65535</collide_bitmask>
              <ode/>
            </contact>
            <friction>
              <ode>
                <mu>100</mu>
                <mu2>50</mu2>
              </ode>
              <torsional><ode/></torsional>
            </friction>
            <bounce/>
          </surface>
          <max_contacts>10</max_contacts>
        </collision>
        <visual name='visual'>
          <cast_shadows>0</cast_shadows>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/DarkGrey</name>
            </script>
          </material>
        </visual>
        <self_collide>0</self_collide>
        <enable_wind>0</enable_wind>
        <kinematic>0</kinematic>
      </link>
    </model>
    <gravity>0 0 -9.8</gravity>
    <magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>
    <atmosphere type='adiabatic'/>
    <physics type='ode'>
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1</real_time_factor>
      <real_time_update_rate>1000</real_time_update_rate>
    </physics>
    <scene>
      <ambient>0.6 0.6 0.6 1</ambient>
      <background>0.7 0.7 0.7 1</background>
      <shadows>0</shadows>
    </scene>
    <audio>
      <device>none</device>
    </audio>
    <wind/>
    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <latitude_deg>0</latitude_deg>
      <longitude_deg>0</longitude_deg>
      <elevation>0</elevation>
      <heading_deg>0</heading_deg>
    </spherical_coordinates>

{tiles_str}

    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose>0.0 -0.2 2.2 0 1.570796 1.570796</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>
"""

destinations = [
    'src/articubot_one/worlds/circle_world.world',
    'src/articubot_one/worlds/circuito_8_tiles.world',
    'worlds/circle_world.world',
    'worlds/circuito_8_tiles.world',
    'gazebo_world/circle_world.world',
]

for d in destinations:
    os.makedirs(os.path.dirname(d), exist_ok=True)
    with open(d, 'w', encoding='utf-8') as f:
        f.write(world_content)
    ET.parse(d)
    print('Validated & Wrote', d)
