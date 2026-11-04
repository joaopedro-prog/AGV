"""
Complete generator and world cleaner.
1. Generates pista_completa_plana.world in src/articubot_one/worlds/ and worlds/
2. Retains pista_teste_8_tiles.world
3. Deletes all other .world files from src/articubot_one/worlds/ and worlds/ and gazebo_world/
"""

import os
import glob
import xml.etree.ElementTree as ET
import math

SCALE = 4.0
TILE_SIZE = 0.30 * SCALE  # 1.20m

def create_white_world_header():
    return f"""<sdf version='1.7'>
  <world name='default'>
    <!-- Iluminacao Zenital Sem Sombras (Piso Claro e Linhas Pretas de Alto Contraste) -->
    <light name='sun' type='directional'>
      <cast_shadows>0</cast_shadows>
      <pose>0 0 20 0 0 0</pose>
      <diffuse>0.95 0.95 0.95 1</diffuse>
      <specular>0.05 0.05 0.05 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>0 0 -1</direction>
    </light>

    <!-- Fundo Branco Total (Sky / Horizon) -->
    <scene>
      <ambient>0.95 0.95 0.95 1</ambient>
      <background>1 1 1 1</background>
      <shadows>0</shadows>
      <grid>0</grid>
    </scene>

    <!-- Chao Branco Total (Gazebo/White) para Contraste Maximo com as Linhas Pretas -->
    <model name='ground_plane'>
      <static>1</static>
      <link name='link'>
        <collision name='collision'>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>200 200</size>
            </plane>
          </geometry>
          <surface>
            <contact><collide_bitmask>65535</collide_bitmask><ode/></contact>
            <friction>
              <ode><mu>100</mu><mu2>50</mu2></ode>
              <torsional><ode/></torsional>
            </friction>
            <bounce/>
          </surface>
        </collision>
        <visual name='visual'>
          <cast_shadows>0</cast_shadows>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>200 200</size>
            </plane>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
            <ambient>1 1 1 1</ambient>
            <diffuse>1 1 1 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
          </material>
        </visual>
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
    <audio><device>none</device></audio>
"""

def generate_tiles():
    tiles = []

    # 1. ANEL EXTERNO (OUTER PERIMETER LOOP) 6.0m x 3.6m
    # Topo (Y = 1.80, X de -2.40 a +2.40: 4 tiles retos)
    tiles.append(('tile_top_1', 'tile-reta', [-2.40, 1.80 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_top_2', 'tile-reta', [-1.20, 1.80 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_top_3', 'tile-reta', [ 0.00, 1.80 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_top_4', 'tile-reta', [ 1.20, 1.80 + 0.60, 0.001, 0, 0, 0.0]))

    # Curva Canto Superior Direito (TR: de (2.40, 1.80) a (3.00, 1.20))
    tiles.append(('tile_curva_tr', 'tile-curva', [2.40, 1.80 + 0.60, 0.001, 0, 0, 0.0]))

    # Lado Direito (X = 3.00, Y de 1.20 a -1.20: 2 tiles retos)
    tiles.append(('tile_right_1', 'tile-reta', [3.00 + 0.60,  1.20, 0.001, 0, 0, -math.pi/2]))
    tiles.append(('tile_right_2', 'tile-reta', [3.00 + 0.60,  0.00, 0.001, 0, 0, -math.pi/2]))

    # Curva Canto Inferior Direito (BR: de (3.00, -1.20) a (2.40, -1.80))
    tiles.append(('tile_curva_br', 'tile-curva', [3.00 + 0.60, -1.20, 0.001, 0, 0, -math.pi/2]))

    # Fundo (Y = -1.80, X de 2.40 a -2.40: 4 tiles retos)
    tiles.append(('tile_bottom_1', 'tile-reta', [ 2.40, -1.80 - 0.60, 0.001, 0, 0, math.pi]))
    tiles.append(('tile_bottom_2', 'tile-reta', [ 1.20, -1.80 - 0.60, 0.001, 0, 0, math.pi]))
    tiles.append(('tile_bottom_3', 'tile-reta', [ 0.00, -1.80 - 0.60, 0.001, 0, 0, math.pi]))
    tiles.append(('tile_bottom_4', 'tile-reta', [-1.20, -1.80 - 0.60, 0.001, 0, 0, math.pi]))

    # Curva Canto Inferior Esquerdo (BL: de (-2.40, -1.80) a (-3.00, -1.20))
    tiles.append(('tile_curva_bl', 'tile-curva', [-2.40, -1.80 - 0.60, 0.001, 0, 0, math.pi]))

    # Lado Esquerdo (X = -3.00, Y de -1.20 a +1.20: 2 tiles retos)
    tiles.append(('tile_left_1', 'tile-reta', [-3.00 - 0.60, -1.20, 0.001, 0, 0, math.pi/2]))
    tiles.append(('tile_left_2', 'tile-reta', [-3.00 - 0.60,  0.00, 0.001, 0, 0, math.pi/2]))

    # Curva Canto Superior Esquerdo (TL: de (-3.00, 1.20) a (-2.40, 1.80))
    tiles.append(('tile_curva_tl', 'tile-curva', [-3.00 - 0.60, 1.20, 0.001, 0, 0, math.pi/2]))

    # 2. CORREDOR CENTRAL HORIZONTAL (Y = 0.0, de X = -3.00 a +3.00)
    tiles.append(('tile_mid_h1', 'tile-reta', [-3.00, 0.00 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_mid_h2', 'tile-reta', [-1.80, 0.00 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_mid_h3', 'tile-reta', [-0.60, 0.00 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_mid_h4', 'tile-reta', [ 0.60, 0.00 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_mid_h5', 'tile-reta', [ 1.80, 0.00 + 0.60, 0.001, 0, 0, 0.0]))

    # 3. CORREDOR CENTRAL VERTICAL (X = 0.0, de Y = 1.80 a -1.80)
    tiles.append(('tile_mid_v1', 'tile-reta', [0.00 + 0.60,  1.80, 0.001, 0, 0, -math.pi/2]))
    tiles.append(('tile_mid_v2', 'tile-reta', [0.00 + 0.60,  0.60, 0.001, 0, 0, -math.pi/2]))
    tiles.append(('tile_mid_v3', 'tile-reta', [0.00 + 0.60, -0.60, 0.001, 0, 0, -math.pi/2]))

    # 4. ROTATÓRIA CENTRAL / BYPASS EM CURVA
    tiles.append(('tile_bypass_ne', 'tile-curva', [0.00, 0.60 + 0.60, 0.001, 0, 0, 0.0]))
    tiles.append(('tile_bypass_se', 'tile-curva', [0.60 + 0.60, 0.00, 0.001, 0, 0, -math.pi/2]))
    tiles.append(('tile_bypass_sw', 'tile-curva', [0.00, -0.60 - 0.60, 0.001, 0, 0, math.pi]))
    tiles.append(('tile_bypass_nw', 'tile-curva', [-0.60 - 0.60, 0.00, 0.001, 0, 0, math.pi/2]))

    return tiles

def build_world_content():
    tiles = generate_tiles()
    models_xml = []

    for name, folder, pose in tiles:
        mesh_name = 'tile_reta.dae' if folder == 'tile-reta' else 'tile_curva.dae'
        x, y, z, r, p, yaw = pose
        xml = f"""    <model name='{name}'>
      <static>1</static>
      <link name='link'>
        <visual name='visual'>
          <pose>0 0 0 1.5708 -0 0</pose>
          <geometry>
            <mesh>
              <uri>/workspace/tiles/{folder}/meshes/{mesh_name}</uri>
              <scale>{SCALE} 1 {SCALE}</scale>
            </mesh>
          </geometry>
        </visual>
        <collision name='collision'>
          <geometry>
            <box>
              <size>{TILE_SIZE:.2f} {TILE_SIZE:.2f} 0.003</size>
            </box>
          </geometry>
          <surface>
            <contact><ode/></contact>
            <friction>
              <ode><mu>100</mu><mu2>50</mu2></ode>
              <torsional><ode/></torsional>
            </friction>
          </surface>
        </collision>
      </link>
      <pose>{x:.4f} {y:.4f} {z:.4f} {r:.4f} {p:.4f} {yaw:.6f}</pose>
    </model>"""
        models_xml.append(xml)

    tiles_str = "\n\n".join(models_xml)
    return f"""{create_white_world_header()}

{tiles_str}

    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose>0.0 -1.0 10.0 0 1.5708 1.5708</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>"""

def main():
    content = build_world_content()
    # Validate
    ET.fromstring(content)
    print("XML valid!")

    target_paths = [
        'src/articubot_one/worlds/pista_completa_plana.world',
        'worlds/pista_completa_plana.world'
    ]
    for tp in target_paths:
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        with open(tp, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[CRIADO] {tp}")

    # Exclude all worlds other than pista_teste_8_tiles.world and pista_completa_plana.world
    keep = {'pista_teste_8_tiles.world', 'pista_completa_plana.world'}
    for d in ['src/articubot_one/worlds', 'worlds', 'gazebo_world']:
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.world'):
                if f not in keep:
                    full_p = os.path.join(d, f)
                    try:
                        os.remove(full_p)
                        print(f"[REMOVIDO] {full_p}")
                    except Exception as e:
                        print(f"[ERRO REMOCAO] {full_p}: {e}")

if __name__ == '__main__':
    main()
