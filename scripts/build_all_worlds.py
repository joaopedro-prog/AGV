import math
import os
import xml.etree.ElementTree as ET

"""
Gerador Completo de Mundos para o AGV Gazebo:
1. pista_completa_3d.world (NOVA: Pista 3D com rampas, viaduto e travessia inferior)
2. Atualização de iluminação natural realista em todas as pistas
3. Nomenclatura profissional e clara
"""

# ==============================================================================
# 1. CONSTRUÇÃO DA PISTA 3D MULTINÍVEL (pista_completa_3d.world)
# ==============================================================================

# Plan Suzuka-style Overpass Circuit
# 32 segments, perfectly closed:
plan = [
    # --- Setor 1: Reta Térrea Principal (Passa por debaixo da ponte em X=-0.15) ---
    ('tile_reta_g1', 'tile-reta', 'S', 0.0),    # (-0.6, 0.0) -> (-0.3, 0.0)
    ('tile_reta_tunnel', 'tile-reta', 'S', 0.0),# (-0.3, 0.0) -> ( 0.0, 0.0)  <-- VÃO INFERIOR DA PONTE!
    ('tile_reta_g3', 'tile-reta', 'S', 0.0),    # ( 0.0, 0.0) -> ( 0.3, 0.0)
    ('tile_reta_g4', 'tile-reta', 'S', 0.0),    # ( 0.3, 0.0) -> ( 0.6, 0.0)
    
    # --- Setor 2: Curva e Reta Lateral Direita ---
    ('tile_curva_r1', 'tile-curva', 'R', 0.0),  # ( 0.6, 0.0) -> ( 0.75, -0.15)
    ('tile_reta_r2', 'tile-reta', 'S', 0.0),    # ( 0.75, -0.15) -> ( 0.75, -0.45)
    ('tile_reta_r3', 'tile-reta', 'S', 0.0),    # ( 0.75, -0.45) -> ( 0.75, -0.75)
    
    # --- Setor 3: Contorno Sul Térreo ---
    ('tile_curva_r4', 'tile-curva', 'R', 0.0),  # ( 0.75, -0.75) -> ( 0.6, -0.9)
    ('tile_reta_s1', 'tile-reta', 'S', 0.0),    # ( 0.6, -0.9) -> ( 0.3, -0.9)
    ('tile_reta_s2', 'tile-reta', 'S', 0.0),    # ( 0.3, -0.9) -> ( 0.0, -0.9)
    ('tile_reta_s3', 'tile-reta', 'S', 0.0),    # ( 0.0, -0.9) -> (-0.3, -0.9)
    ('tile_reta_s4', 'tile-reta', 'S', 0.0),    # (-0.3, -0.9) -> (-0.6, -0.9)
    ('tile_reta_s5', 'tile-reta', 'S', 0.0),    # (-0.6, -0.9) -> (-0.9, -0.9)
    
    # --- Setor 4: Entrada na Rampa Oeste ---
    ('tile_curva_w1', 'tile-curva', 'R', 0.0),  # (-0.9, -0.9) -> (-1.05, -0.75)
    ('tile_reta_w2', 'tile-reta', 'S', 0.0),    # (-1.05, -0.75) -> (-1.05, -0.45)
    
    # --- Setor 5: RAMPA DE SUBIDA (Incline ~16.7 graus, sobe +18 cm) ---
    ('tile_rampa_subida_1', 'tile-reta', 'S', 0.09), # (-1.05, -0.45) -> (-1.05, -0.15, z: 0.001 -> 0.091)
    ('tile_rampa_subida_2', 'tile-reta', 'S', 0.09), # (-1.05, -0.15) -> (-1.05,  0.15, z: 0.091 -> 0.181)
    
    # --- Setor 6: Platô Elevado Norte (Z = 0.181m) ---
    ('tile_reta_topo_w', 'tile-reta', 'S', 0.0),    # (-1.05, 0.15) -> (-1.05, 0.45, z: 0.181)
    ('tile_curva_topo_nw', 'tile-curva', 'R', 0.0), # (-1.05, 0.45) -> (-0.9, 0.6, z: 0.181)
    ('tile_reta_topo_n1', 'tile-reta', 'S', 0.0),   # (-0.9, 0.6) -> (-0.6, 0.6, z: 0.181)
    ('tile_reta_topo_n2', 'tile-reta', 'S', 0.0),   # (-0.6, 0.6) -> (-0.3, 0.6, z: 0.181)
    ('tile_curva_topo_ne', 'tile-curva', 'R', 0.0), # (-0.3, 0.6) -> (-0.15, 0.45, z: 0.181)
    
    # --- Setor 7: PONTE ELEVADA (VIADUTO SOBRE A RETA TÉRREA!) ---
    ('tile_reta_bridge_app', 'tile-reta', 'S', 0.0), # (-0.15, 0.45) -> (-0.15, 0.15, z: 0.181)
    ('tile_reta_viaduto', 'tile-reta', 'S', 0.0),    # (-0.15, 0.15) -> (-0.15, -0.15, z: 0.181) <-- CRUZA POR CIMA!
    
    # --- Setor 8: RAMPA DE DESCIDA (Decline, desce -18 cm até o solo) ---
    ('tile_rampa_descida_1', 'tile-reta', 'S', -0.09), # (-0.15, -0.15) -> (-0.15, -0.45, z: 0.181 -> 0.091)
    ('tile_rampa_descida_2', 'tile-reta', 'S', -0.09), # (-0.15, -0.45) -> (-0.15, -0.75, z: 0.091 -> 0.001)
    
    # --- Setor 9: Retorno Conectando ao Início Térreo ---
    ('tile_curva_ret_1', 'tile-curva', 'R', 0.0), # (-0.15, -0.75) -> (-0.3, -0.9, z: 0.001)
    ('tile_reta_ret_2', 'tile-reta', 'S', 0.0),   # (-0.3, -0.9) -> (-0.6, -0.9, z: 0.001)
    ('tile_curva_ret_3', 'tile-curva', 'R', 0.0), # (-0.6, -0.9) -> (-0.75, -0.75, z: 0.001)
    ('tile_reta_ret_4', 'tile-reta', 'S', 0.0),   # (-0.75, -0.75) -> (-0.75, -0.45, z: 0.001)
    ('tile_reta_ret_5', 'tile-reta', 'S', 0.0),   # (-0.75, -0.45) -> (-0.75, -0.15, z: 0.001)
    ('tile_curva_ret_6', 'tile-curva', 'R', 0.0), # (-0.75, -0.15) -> (-0.6, 0.0, z: 0.001) <-- FECHA PERFEITAMENTE!
]

def step(pos, el, dz=0.0):
    x, y, z, yaw = pos
    if el == 'S':
        return (round(x + 0.30*math.cos(yaw), 4), round(y + 0.30*math.sin(yaw), 4), round(z + dz, 4), yaw)
    elif el == 'R':
        cx = x + 0.15*math.sin(yaw)
        cy = y - 0.15*math.cos(yaw)
        ny = (yaw - math.pi/2) % (2*math.pi)
        ex = cx - 0.15*math.sin(ny)
        ey = cy + 0.15*math.cos(ny)
        return (round(ex, 4), round(ey, 4), z, round(ny, 4))

pos = (-0.60, 0.0, 0.001, 0.0)
models_xml = []

for name, folder, el, dz in plan:
    p1 = pos
    p2 = step(pos, el, dz)
    x1, y1, z1, yaw1 = p1
    
    # Calculate Gazebo model pose
    mx = x1 - 0.15 * math.sin(yaw1)
    my = y1 + 0.15 * math.cos(yaw1)
    mz = z1
    
    pitch = 0.0
    if abs(dz) > 1e-4:
        pitch = -math.asin(dz / 0.30)
    
    mesh_name = 'tile_reta.dae' if folder == 'tile-reta' else 'tile_curva.dae'
    
    xml = f"""    <model name='{name}'>
      <static>1</static>
      <link name='link'>
        <visual name='visual'>
          <pose>0 0 0 1.5708 -0 0</pose>
          <geometry>
            <mesh>
              <uri>/workspace/tiles/{folder}/meshes/{mesh_name}</uri>
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
          <surface>
            <contact><ode/></contact>
            <friction>
              <ode><mu>100</mu><mu2>50</mu2></ode>
              <torsional><ode/></torsional>
            </friction>
          </surface>
        </collision>
      </link>
      <pose>{mx:.4f} {my:.4f} {mz:.4f} 0 {pitch:.6f} {yaw1:.6f}</pose>
    </model>"""
    models_xml.append(xml)
    pos = p2

# Pilares estruturais do viaduto (estéticos e realistas)
pillars = [
    ('pillar_nw', -0.32,  0.15, 0.09, 0.18),
    ('pillar_ne',  0.02,  0.15, 0.09, 0.18),
    ('pillar_sw', -0.32, -0.15, 0.09, 0.18),
    ('pillar_se',  0.02, -0.15, 0.09, 0.18),
    ('pillar_n_top', -0.60, 0.45, 0.09, 0.18),
    ('pillar_w_top', -1.22, 0.15, 0.09, 0.18),
    ('pillar_e_top', -0.88, 0.15, 0.09, 0.18),
]

for pname, px, py, pz, ph in pillars:
    pxml = f"""    <model name='{pname}'>
      <static>1</static>
      <link name='link'>
        <visual name='visual'>
          <geometry>
            <cylinder>
              <radius>0.015</radius>
              <length>{ph}</length>
            </cylinder>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
          </material>
        </visual>
        <collision name='collision'>
          <geometry>
            <cylinder>
              <radius>0.015</radius>
              <length>{ph}</length>
            </cylinder>
          </geometry>
        </collision>
      </link>
      <pose>{px:.4f} {py:.4f} {pz:.4f} 0 0 0</pose>
    </model>"""
    models_xml.append(pxml)

tiles_str = "\n\n".join(models_xml)

natural_world_xml = f"""<sdf version='1.7'>
  <world name='default'>
    <!-- Iluminacao Natural Solar Suave (Sem ofuscamento, com sombras realistas) -->
    <light name='sun' type='directional'>
      <cast_shadows>1</cast_shadows>
      <pose>5 5 10 0 0.45 0.75</pose>
      <diffuse>0.85 0.85 0.82 1</diffuse>
      <specular>0.15 0.15 0.15 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.45 -0.45 -0.77</direction>
    </light>

    <scene>
      <ambient>0.45 0.45 0.45 1</ambient>
      <background>0.65 0.75 0.85 1</background>
      <shadows>1</shadows>
    </scene>

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

    <audio>
      <device>none</device>
    </audio>

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
        <pose>0.8 -1.8 1.8 0 0.65 2.15</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>
"""

# Salva pista_completa_3d.world nas pastas necessárias
pista_3d_paths = [
    'src/articubot_one/worlds/pista_completa_3d.world',
    'worlds/pista_completa_3d.world',
    'gazebo_world/pista_completa_3d.world',
]
for p in pista_3d_paths:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(natural_world_xml)
    ET.parse(p)
    print('Validated & Wrote 3D World:', p)

# ==============================================================================
# 2. ATUALIZAR ILUMINAÇÃO NATURAL EM TODOS OS MUNDOS EXISTENTES
# ==============================================================================
def apply_natural_lighting(file_path):
    if not os.path.isfile(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        t = f.read()
    
    # 1. Ajusta ambient e background para céu natural e contraste suave
    t = t.replace('<ambient>0.85 0.85 0.85 1</ambient>', '<ambient>0.45 0.45 0.45 1</ambient>')
    t = t.replace('<ambient>0.6 0.6 0.6 1</ambient>', '<ambient>0.45 0.45 0.45 1</ambient>')
    t = t.replace('<background>0.8 0.8 0.8 1</background>', '<background>0.65 0.75 0.85 1</background>')
    t = t.replace('<background>0.7 0.7 0.7 1</background>', '<background>0.65 0.75 0.85 1</background>')
    t = t.replace('<shadows>0</shadows>', '<shadows>1</shadows>')
    
    # 2. Ajusta sol para iluminação suave e angulada (sem queimar a imagem)
    t = t.replace('<diffuse>1 1 1 1</diffuse>', '<diffuse>0.85 0.85 0.82 1</diffuse>')
    t = t.replace('<diffuse>1.0 1.0 1.0 1</diffuse>', '<diffuse>0.85 0.85 0.82 1</diffuse>')
    t = t.replace('<specular>0.3 0.3 0.3 1</specular>', '<specular>0.15 0.15 0.15 1</specular>')
    t = t.replace('<specular>0.2 0.2 0.2 1</specular>', '<specular>0.15 0.15 0.15 1</specular>')
    t = t.replace('<direction>0 0 -1</direction>', '<direction>-0.45 -0.45 -0.77</direction>')
    t = t.replace('<pose>0 0 5 0 0 0</pose>', '<pose>5 5 10 0 0.45 0.75</pose>')
    t = t.replace('<pose>0 0 5 0 -0 0</pose>', '<pose>5 5 10 0 0.45 0.75</pose>')
    
    # 3. Piso escuro para alto contraste com as placas brancas
    t = t.replace('<name>Gazebo/Grey</name>', '<name>Gazebo/DarkGrey</name>')
    
    # 4. Remove luzes secundárias ofuscantes
    import re
    t = re.sub(r'<light name=\'overhead_light\'.*?</light>', '', t, flags=re.DOTALL)
    t = re.sub(r'<light name="light_overhead_\d+".*?</light>', '', t, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(t)
    try:
        ET.parse(file_path)
        print('Natural lighting updated & validated:', file_path)
    except Exception as exc:
        print('XML Error after lighting update in', file_path, exc)

worlds_to_update = [
    'src/articubot_one/worlds/circuit1.world',
    'worlds/circuit1.world',
    'src/articubot_one/worlds/circuito_8_tiles.world',
    'worlds/circuito_8_tiles.world',
    'src/articubot_one/worlds/circle_world.world',
    'worlds/circle_world.world',
    'src/articubot_one/worlds/obstacles.world',
    'worlds/obstacles.world',
]
for w in worlds_to_update:
    apply_natural_lighting(w)

# ==============================================================================
# 3. CRIAÇÃO DE CÓPIAS COM NOMES CLAROS E DESCRITIVOS (PT-BR)
# ==============================================================================
pairs = [
    ('src/articubot_one/worlds/circuit1.world', 'src/articubot_one/worlds/pista_oficial.world'),
    ('worlds/circuit1.world', 'worlds/pista_oficial.world'),
    ('src/articubot_one/worlds/circuito_8_tiles.world', 'src/articubot_one/worlds/pista_teste_8_tiles.world'),
    ('worlds/circuito_8_tiles.world', 'worlds/pista_teste_8_tiles.world'),
    ('src/articubot_one/worlds/obstacles.world', 'src/articubot_one/worlds/pista_obstaculos.world'),
    ('worlds/obstacles.world', 'worlds/pista_obstaculos.world'),
    ('src/articubot_one/worlds/empty.world', 'src/articubot_one/worlds/mundo_vazio.world'),
    ('worlds/empty.world', 'worlds/mundo_vazio.world'),
]
for src, dst in pairs:
    if os.path.exists(src):
        with open(src, 'r', encoding='utf-8') as sf:
            content = sf.read()
        with open(dst, 'w', encoding='utf-8') as df:
            df.write(content)
        print(f'Created clear name: {dst}')
