#!/usr/bin/env python3
"""
Escalador Completo dos Mundos do Gazebo para o Robô Real (AGV):
1. Escala os tiles por 4.0x:
   - Tamanho do tile: 0.30m -> 1.20m
   - Raio das curvas: 0.15m -> 0.60m (suave para o AGV com bitola de 0.468m)
   - Escala das malhas 3D: <scale>4.0 1.0 4.0</scale>
   - Caixa de colisão: <size>1.20 1.20 0.003</size>
2. Fundo e chão PURE WHITE (Branco Total):
   - Chão: Gazebo/White em todo o plano de 200x200m
   - Cena: Background (1, 1, 1, 1), Ambient (0.95, 0.95, 0.95, 1)
   - Sem sombras no chão (<shadows>0</shadows>, <cast_shadows>0</cast_shadows>)
   - Contraste perfeito: chão 100% branco e linhas de fita 100% pretas
3. Atualiza pista_completa_3d, pista_teste_8_tiles, pista_oficial, pista_obstaculos, mundo_vazio
4. Sincroniza em src/articubot_one/worlds e worlds/
"""

import math
import os
import re
import xml.etree.ElementTree as ET

SCALE = 4.0
TILE_SIZE = 0.30 * SCALE  # 1.20m
CURVE_RADIUS = 0.15 * SCALE  # 0.60m

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

# ==============================================================================
# 1. PISTA TESTE 8 TILES (ESTADIO 8 TILES ESCALADO 4x: 3.6m x 3.6m, R=0.60m)
# ==============================================================================
def build_pista_8_tiles():
    # Coordenadas escaladas (0.15 * 4 = 0.60; 0.45 * 4 = 1.80)
    tiles_def = [
        ('tile_reta_top',    'tile-reta',  -0.60,  1.80, 0.001, 0.0, 0.0,  0.0),
        ('tile_curva_tr',   'tile-curva',  0.60,  1.80, 0.001, 0.0, 0.0,  0.0),
        ('tile_reta_right',  'tile-reta',   1.80,  0.60, 0.001, 0.0, 0.0, -math.pi/2),
        ('tile_curva_br',   'tile-curva',  1.80, -0.60, 0.001, 0.0, 0.0, -math.pi/2),
        ('tile_reta_bottom', 'tile-reta',   0.60, -1.80, 0.001, 0.0, 0.0,  math.pi),
        ('tile_curva_bl',   'tile-curva', -0.60, -1.80, 0.001, 0.0, 0.0,  math.pi),
        ('tile_reta_left',   'tile-reta',  -1.80, -0.60, 0.001, 0.0, 0.0,  math.pi/2),
        ('tile_curva_tl',   'tile-curva', -1.80,  0.60, 0.001, 0.0, 0.0,  math.pi/2),
    ]

    xml_parts = [create_white_world_header()]
    for name, folder, x, y, z, r, p, yaw in tiles_def:
        mesh_name = 'tile_reta.dae' if folder == 'tile-reta' else 'tile_curva.dae'
        xml_parts.append(f"""    <model name='{name}'>
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
    </model>""")

    xml_parts.append("""    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose>0.0 -0.5 6.0 0 1.5708 1.5708</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>""")
    return "\n\n".join(xml_parts)


# ==============================================================================
# 2. PISTA COMPLETA 3D (3D SUZUKA OVERPASS ESCALADO 4x: R=0.60m, Z_PONTE=0.50m)
# ==============================================================================
def build_pista_3d():
    # 32 segmentos perfeitamente fechados
    # L = 1.20m, R = 0.60m, ramp dz = 0.25m (sobe 0.50m em 2 tiles de 1.20m, slope suave de ~12 graus)
    L = TILE_SIZE       # 1.20m
    R = CURVE_RADIUS   # 0.60m
    DZ = 0.25          # 25 cm por tile

    plan = [
        # --- Setor 1: Reta Terrea Principal (Passa por debaixo da ponte em X=0) ---
        ('tile_reta_g1', 'tile-reta', 'S', 0.0),
        ('tile_reta_tunnel', 'tile-reta', 'S', 0.0), # <-- VAO INFERIOR DA PONTE ELEVADA!
        ('tile_reta_g3', 'tile-reta', 'S', 0.0),
        ('tile_reta_g4', 'tile-reta', 'S', 0.0),
        
        # --- Setor 2: Curva e Reta Lateral Direita ---
        ('tile_curva_r1', 'tile-curva', 'R', 0.0),
        ('tile_reta_r2', 'tile-reta', 'S', 0.0),
        ('tile_reta_r3', 'tile-reta', 'S', 0.0),
        
        # --- Setor 3: Contorno Sul Terreo ---
        ('tile_curva_r4', 'tile-curva', 'R', 0.0),
        ('tile_reta_s1', 'tile-reta', 'S', 0.0),
        ('tile_reta_s2', 'tile-reta', 'S', 0.0),
        ('tile_reta_s3', 'tile-reta', 'S', 0.0),
        ('tile_reta_s4', 'tile-reta', 'S', 0.0),
        ('tile_reta_s5', 'tile-reta', 'S', 0.0),
        
        # --- Setor 4: Entrada na Rampa Oeste ---
        ('tile_curva_w1', 'tile-curva', 'R', 0.0),
        ('tile_reta_w2', 'tile-reta', 'S', 0.0),
        
        # --- Setor 5: RAMPA DE SUBIDA (2 tiles de 1.20m, sobe +0.50m suavemente) ---
        ('tile_rampa_subida_1', 'tile-reta', 'S', DZ),
        ('tile_rampa_subida_2', 'tile-reta', 'S', DZ),
        
        # --- Setor 6: Plato Elevado Norte (Z = 0.501m) ---
        ('tile_reta_topo_w', 'tile-reta', 'S', 0.0),
        ('tile_curva_topo_nw', 'tile-curva', 'R', 0.0),
        ('tile_reta_topo_n1', 'tile-reta', 'S', 0.0),
        ('tile_reta_topo_n2', 'tile-reta', 'S', 0.0),
        ('tile_curva_topo_ne', 'tile-curva', 'R', 0.0),
        
        # --- Setor 7: PONTE ELEVADA (VIADUTO SOBRE A RETA TERREA A Z = 0.501m) ---
        ('tile_reta_bridge_app', 'tile-reta', 'S', 0.0),
        ('tile_reta_viaduto', 'tile-reta', 'S', 0.0), # <-- CRUZA POR CIMA COM VÃO DE 50 CM!
        
        # --- Setor 8: RAMPA DE DESCIDA (Desce -0.50m ate o solo) ---
        ('tile_rampa_descida_1', 'tile-reta', 'S', -DZ),
        ('tile_rampa_descida_2', 'tile-reta', 'S', -DZ),
        
        # --- Setor 9: Retorno Conectando ao Inicio Terreo ---
        ('tile_curva_ret_1', 'tile-curva', 'R', 0.0),
        ('tile_reta_ret_2', 'tile-reta', 'S', 0.0),
        ('tile_curva_ret_3', 'tile-curva', 'R', 0.0),
        ('tile_reta_ret_4', 'tile-reta', 'S', 0.0),
        ('tile_reta_ret_5', 'tile-reta', 'S', 0.0),
        ('tile_curva_ret_6', 'tile-curva', 'R', 0.0),
    ]

    def step(pos, el, dz=0.0):
        x, y, z, yaw = pos
        if el == 'S':
            return (round(x + L*math.cos(yaw), 4), round(y + L*math.sin(yaw), 4), round(z + dz, 4), yaw)
        elif el == 'R':
            cx = x + R*math.sin(yaw)
            cy = y - R*math.cos(yaw)
            ny = (yaw - math.pi/2) % (2*math.pi)
            ex = cx - R*math.sin(ny)
            ey = cy + R*math.cos(ny)
            return (round(ex, 4), round(ey, 4), z, round(ny, 4))

    pos = (-2.40, 0.0, 0.001, 0.0)
    models_xml = []

    for name, folder, el, dz in plan:
        p1 = pos
        p2 = step(pos, el, dz)
        x1, y1, z1, yaw1 = p1
        
        # Modelo do Gazebo tem origem no centro da placa
        mx = x1 - (L/2) * math.sin(yaw1)
        my = y1 + (L/2) * math.cos(yaw1)
        mz = z1
        
        pitch = 0.0
        if abs(dz) > 1e-4:
            pitch = -math.asin(dz / L)
        
        mesh_name = 'tile_reta.dae' if folder == 'tile-reta' else 'tile_curva.dae'
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
              <size>{L:.2f} {L:.2f} 0.003</size>
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

    # Pilares de sustentação cilíndricos na ponte elevada
    bridge_z = 2 * DZ  # 0.50m
    pillars = [
        ('pillar_nw', -0.90,  0.60, bridge_z/2, bridge_z),
        ('pillar_ne',  0.90,  0.60, bridge_z/2, bridge_z),
        ('pillar_sw', -0.90, -0.60, bridge_z/2, bridge_z),
        ('pillar_se',  0.90, -0.60, bridge_z/2, bridge_z),
        ('pillar_n_top', -2.40, 1.80, bridge_z/2, bridge_z),
        ('pillar_w_top', -4.80, 0.60, bridge_z/2, bridge_z),
        ('pillar_e_top', -3.60, 0.60, bridge_z/2, bridge_z),
    ]

    for pname, px, py, pz, ph in pillars:
        pxml = f"""    <model name='{pname}'>
      <static>1</static>
      <link name='link'>
        <visual name='visual'>
          <geometry>
            <cylinder>
              <radius>0.06</radius>
              <length>{ph:.2f}</length>
            </cylinder>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
          </material>
        </visual>
        <collision name='collision'>
          <geometry>
            <cylinder>
              <radius>0.06</radius>
              <length>{ph:.2f}</length>
            </cylinder>
          </geometry>
        </collision>
      </link>
      <pose>{px:.4f} {py:.4f} {pz:.4f} 0 0 0</pose>
    </model>"""
        models_xml.append(pxml)

    tiles_str = "\n\n".join(models_xml)
    return f"""{create_white_world_header()}

{tiles_str}

    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose>2.5 -6.0 6.5 0 0.65 2.15</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>"""


# ==============================================================================
# 3. PISTA OFICIAL / CIRCUIT1 (ESCALADA 4x COM FUNDO BRANCO)
# ==============================================================================
def scale_existing_world(src_file):
    with open(src_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Substitui ou reconstroi os modelos
    tree = ET.parse(src_file)
    root = tree.getroot()
    world = root.find('world')

    models_xml = []
    for model in world.findall('model'):
        mname = model.get('name')
        if mname == 'ground_plane':
            continue

        pose = model.find('pose')
        if pose is not None and pose.text:
            coords = [float(x) for x in pose.text.strip().split()]
        else:
            coords = [0.0]*6

        # Escala posições X, Y, Z
        nx = coords[0] * SCALE
        ny = coords[1] * SCALE
        nz = coords[2] * SCALE
        r, p, yaw = coords[3], coords[4], coords[5]

        # Descobre mesh
        mesh_elem = model.find('.//mesh')
        uri = mesh_elem.find('uri').text.strip() if mesh_elem is not None else ''
        folder = 'tile-reta' if 'reta' in uri else ('tile-curva90' if 'curva90' in uri else 'tile-curva')
        mesh_file = uri.split('/')[-1] if uri else 'tile_reta.dae'

        # Se for modelo de obstaculo (cone ou barrel)
        if 'Barrel' in mname or 'Cone' in mname:
            m_xml = f"""    <model name='{mname}'>
      <static>1</static>
      <include>
        <uri>model://{mname.split('_')[0] if '_' in mname else mname}</uri>
      </include>
      <pose>{nx:.4f} {ny:.4f} {nz:.4f} {r:.4f} {p:.4f} {yaw:.6f}</pose>
    </model>"""
        else:
            m_xml = f"""    <model name='{mname}'>
      <static>1</static>
      <link name='link'>
        <visual name='visual'>
          <pose>0 0 0 1.5708 -0 0</pose>
          <geometry>
            <mesh>
              <uri>/workspace/tiles/{folder}/meshes/{mesh_file}</uri>
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
      <pose>{nx:.4f} {ny:.4f} {nz:.4f} {r:.4f} {p:.4f} {yaw:.6f}</pose>
    </model>"""
        models_xml.append(m_xml)

    models_str = "\n\n".join(models_xml)
    return f"""{create_white_world_header()}

{models_str}

    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose>1.0 -4.0 6.0 0 0.8 1.8</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>"""


# ==============================================================================
# 4. MUNDO VAZIO TOTALMENTE BRANCO (MUNDO_VAZIO / EMPTY)
# ==============================================================================
def build_empty_white_world():
    return f"""{create_white_world_header()}
    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose>0.0 -3.0 2.0 0 0.5 1.57</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>"""


# ==============================================================================
# 5. GERADOR E GRAVADOR GERAL
# ==============================================================================
def write_world(rel_path, content):
    full_path = os.path.abspath(rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    try:
        ET.parse(full_path)
        print(f"[OK] Gerado e validado XML: {rel_path}")
    except Exception as e:
        print(f"[ERRO XML] Falha em {rel_path}: {e}")

if __name__ == '__main__':
    print("======================================================================")
    print("  GERANDO MUNDOS ESCALADOS (4.0x) COM FUNDO BRANCO E LINHAS PRETAS")
    print("======================================================================")

    # 1. Pista Teste 8 Tiles (e variantes)
    pista_8_xml = build_pista_8_tiles()
    for p in ['src/articubot_one/worlds/pista_teste_8_tiles.world',
              'src/articubot_one/worlds/circuito_8_tiles.world',
              'src/articubot_one/worlds/circle_world.world',
              'worlds/pista_teste_8_tiles.world',
              'worlds/circuito_8_tiles.world',
              'worlds/circle_world.world']:
        write_world(p, pista_8_xml)

    # 2. Pista 3D Completa
    pista_3d_xml = build_pista_3d()
    for p in ['src/articubot_one/worlds/pista_completa_3d.world',
              'worlds/pista_completa_3d.world']:
        write_world(p, pista_3d_xml)

    # 3. Pista Oficial (e variantes)
    pista_oficial_xml = scale_existing_world('src/articubot_one/worlds/pista_oficial.world')
    for p in ['src/articubot_one/worlds/pista_oficial.world',
              'src/articubot_one/worlds/circuit1.world',
              'worlds/pista_oficial.world',
              'worlds/circuit1.world']:
        write_world(p, pista_oficial_xml)

    # 4. Pista Obstáculos (e variantes)
    pista_obs_xml = scale_existing_world('src/articubot_one/worlds/pista_obstaculos.world')
    for p in ['src/articubot_one/worlds/pista_obstaculos.world',
              'src/articubot_one/worlds/obstacles.world',
              'worlds/pista_obstaculos.world',
              'worlds/obstacles.world']:
        write_world(p, pista_obs_xml)

    # 5. Mundo Vazio
    empty_xml = build_empty_white_world()
    for p in ['src/articubot_one/worlds/mundo_vazio.world',
              'src/articubot_one/worlds/empty.world',
              'worlds/mundo_vazio.world',
              'worlds/empty.world']:
        write_world(p, empty_xml)

    print("\nTodos os mundos foram gerados e sincronizados com sucesso!")
