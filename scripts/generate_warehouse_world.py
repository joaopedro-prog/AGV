#!/usr/bin/env python3
"""
generate_warehouse_world.py
---------------------------
Gerador procedural do Mundo de Armazem Fabril / Centro Logistico no Gazebo Classic.

Caracteristicas:
1. Galpao industrial completo com paredes perimetrais, portoes de doca e colunas.
2. Gondolas industriais (porta-paletes) de alta fidelidade com prateleiras e pilares metalicos.
3. Cargas realistas nas gondolas: Pallets de madeira, caixas de papelao corrugado e containers plasticos.
4. Circuito ciclico fechado (closed-loop) com tiles modulares escalados (1.20m, curvas R=0.60m).
5. 5 Marcadores de cores estrategicos no piso (para fusao entre Visao Computacional e Odometria):
   - Estacao 1 (Verde): Doca de Entrada / Abastecimento / Ponto de Partida
   - Estacao 2 (Azul): Corredor de Estoque A (Picking A)
   - Estacao 3 (Ciano): Intersecao Central / Bypass
   - Estacao 4 (Amarelo): Corredor de Estoque B (Picking B)
   - Estacao 5 (Vermelho): Doca de Expedicao / Descarga
6. Iluminacao industrial difusa zenital de alta visibilidade, eliminando sombras duras para OpenCV.
"""

import os
import math

SCALE = 4.0
TILE_SIZE = 0.30 * SCALE  # 1.20m

# ==============================================================================
# CABEÇALHO DO MUNDO (FÍSICA, ILUMINAÇÃO INDUSTRIAL E PISO CLARO)
# ==============================================================================
def create_world_header():
    return """<sdf version='1.7'>
  <world name='default'>
    <!-- Iluminacao Industrial Zenital Suave (Sem Sombras Duras para Visao Computacional) -->
    <light name='sun_industrial' type='directional'>
      <cast_shadows>0</cast_shadows>
      <pose>0 0 25 0 0 0</pose>
      <diffuse>0.95 0.95 0.95 1</diffuse>
      <specular>0.08 0.08 0.08 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>0.05 0.05 -1</direction>
    </light>

    <!-- Luminarias Industriais Distribuidas (Luzes High-Bay) -->
    <light name='bay_light_1' type='point'>
      <cast_shadows>0</cast_shadows>
      <pose>-3.5 2.5 4.5 0 0 0</pose>
      <diffuse>0.88 0.90 0.95 1</diffuse>
      <specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>25</range><constant>0.8</constant><linear>0.02</linear><quadratic>0.005</quadratic></attenuation>
    </light>

    <light name='bay_light_2' type='point'>
      <cast_shadows>0</cast_shadows>
      <pose>3.5 2.5 4.5 0 0 0</pose>
      <diffuse>0.88 0.90 0.95 1</diffuse>
      <specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>25</range><constant>0.8</constant><linear>0.02</linear><quadratic>0.005</quadratic></attenuation>
    </light>

    <light name='bay_light_3' type='point'>
      <cast_shadows>0</cast_shadows>
      <pose>-3.5 -2.5 4.5 0 0 0</pose>
      <diffuse>0.88 0.90 0.95 1</diffuse>
      <specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>25</range><constant>0.8</constant><linear>0.02</linear><quadratic>0.005</quadratic></attenuation>
    </light>

    <light name='bay_light_4' type='point'>
      <cast_shadows>0</cast_shadows>
      <pose>3.5 -2.5 4.5 0 0 0</pose>
      <diffuse>0.88 0.90 0.95 1</diffuse>
      <specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>25</range><constant>0.8</constant><linear>0.02</linear><quadratic>0.005</quadratic></attenuation>
    </light>

    <light name='bay_light_center' type='point'>
      <cast_shadows>0</cast_shadows>
      <pose>0.0 0.0 5.0 0 0 0</pose>
      <diffuse>0.92 0.92 0.95 1</diffuse>
      <specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>30</range><constant>0.8</constant><linear>0.015</linear><quadratic>0.003</quadratic></attenuation>
    </light>

    <!-- Ambiente Global do Armazem -->
    <scene>
      <ambient>0.92 0.92 0.94 1</ambient>
      <background>0.95 0.95 0.98 1</background>
      <shadows>0</shadows>
      <grid>0</grid>
    </scene>

    <!-- Piso Industrial de Concreto Polido Claro (Alto Atrito e Contraste com Linhas Pretas) -->
    <model name='ground_plane'>
      <static>1</static>
      <link name='link'>
        <collision name='collision'>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>150 150</size>
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
              <size>150 150</size>
            </plane>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/White</name>
            </script>
            <ambient>0.98 0.98 0.98 1</ambient>
            <diffuse>0.98 0.98 0.98 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <!-- Parametros Fisicos ODE para Estabilidade Dinamica -->
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
# ESTRUTURA DO GALPÃO: PAREDES, PORTÕES DE DOCA E COLUNAS
# ==============================================================================
def generate_warehouse_structure():
    models = []
    
    # Dimensoes do galpao: 16m (X: -8.0 a +8.0) x 12m (Y: -6.0 a +6.0), Altura 4.5m
    # 1. Parede Norte (Y = +6.0)
    models.append("""    <!-- Parede Perimetral Norte -->
    <model name='parede_norte'>
      <static>1</static>
      <pose>0.0 6.0 2.25 0 0 0</pose>
      <link name='link'>
        <collision name='col'><geometry><box><size>16.2 0.3 4.5</size></box></geometry></collision>
        <visual name='vis'>
          <geometry><box><size>16.2 0.3 4.5</size></box></geometry>
          <material>
            <script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script>
            <ambient>0.75 0.77 0.80 1</ambient><diffuse>0.75 0.77 0.80 1</diffuse>
          </material>
        </visual>
      </link>
    </model>""")

    # 2. Parede Sul (Y = -6.0)
    models.append("""    <!-- Parede Perimetral Sul -->
    <model name='parede_sul'>
      <static>1</static>
      <pose>0.0 -6.0 2.25 0 0 0</pose>
      <link name='link'>
        <collision name='col'><geometry><box><size>16.2 0.3 4.5</size></box></geometry></collision>
        <visual name='vis'>
          <geometry><box><size>16.2 0.3 4.5</size></box></geometry>
          <material>
            <script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script>
            <ambient>0.75 0.77 0.80 1</ambient><diffuse>0.75 0.77 0.80 1</diffuse>
          </material>
        </visual>
      </link>
    </model>""")

    # 3. Parede Oeste (X = -8.0) com Portao de Doca de Entrada
    models.append("""    <!-- Parede Oeste com Doca de Entrada -->
    <model name='parede_oeste_1'>
      <static>1</static>
      <pose>-8.0 -2.0 2.25 0 0 0</pose>
      <link name='link'>
        <collision name='col'><geometry><box><size>0.3 8.0 4.5</size></box></geometry></collision>
        <visual name='vis'>
          <geometry><box><size>0.3 8.0 4.5</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script></material>
        </visual>
      </link>
    </model>
    <model name='parede_oeste_2'>
      <static>1</static>
      <pose>-8.0 5.0 2.25 0 0 0</pose>
      <link name='link'>
        <collision name='col'><geometry><box><size>0.3 2.0 4.5</size></box></geometry></collision>
        <visual name='vis'>
          <geometry><box><size>0.3 2.0 4.5</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script></material>
        </visual>
      </link>
    </model>
    <!-- Portao da Doca de Entrada (Inbound Bay) -->
    <model name='portao_doca_entrada'>
      <static>1</static>
      <pose>-8.0 3.0 2.25 0 0 0</pose>
      <link name='link'>
        <visual name='vis'>
          <geometry><box><size>0.1 2.8 4.2</size></box></geometry>
          <material>
            <script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/ZincYellow</name></script>
            <ambient>0.90 0.80 0.2 1</ambient><diffuse>0.90 0.80 0.2 1</diffuse>
          </material>
        </visual>
      </link>
    </model>""")

    # 4. Parede Leste (X = +8.0) com Portao de Doca de Expedicao
    models.append("""    <!-- Parede Leste com Doca de Expedicao -->
    <model name='parede_leste_1'>
      <static>1</static>
      <pose>8.0 2.0 2.25 0 0 0</pose>
      <link name='link'>
        <collision name='col'><geometry><box><size>0.3 8.0 4.5</size></box></geometry></collision>
        <visual name='vis'>
          <geometry><box><size>0.3 8.0 4.5</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script></material>
        </visual>
      </link>
    </model>
    <model name='parede_leste_2'>
      <static>1</static>
      <pose>8.0 -5.0 2.25 0 0 0</pose>
      <link name='link'>
        <collision name='col'><geometry><box><size>0.3 2.0 4.5</size></box></geometry></collision>
        <visual name='vis'>
          <geometry><box><size>0.3 2.0 4.5</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/Grey</name></script></material>
        </visual>
      </link>
    </model>
    <!-- Portao da Doca de Expedicao (Outbound Bay) -->
    <model name='portao_doca_expedicao'>
      <static>1</static>
      <pose>8.0 -3.0 2.25 0 0 0</pose>
      <link name='link'>
        <visual name='vis'>
          <geometry><box><size>0.1 2.8 4.2</size></box></geometry>
          <material>
            <script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/ZincYellow</name></script>
            <ambient>0.90 0.80 0.2 1</ambient><diffuse>0.90 0.80 0.2 1</diffuse>
          </material>
        </visual>
      </link>
    </model>""")

    # 5. Colunas Estruturais Industriais (Pilares I-Beam)
    colunas_poses = [
        (-5.5,  4.5), ( 0.0,  4.5), ( 5.5,  4.5),
        (-5.5, -4.5), ( 0.0, -4.5), ( 5.5, -4.5)
    ]
    for idx, (cx, cy) in enumerate(colunas_poses, start=1):
        models.append(f"""    <model name='coluna_industrial_{idx}'>
      <static>1</static>
      <pose>{cx:.2f} {cy:.2f} 2.25 0 0 0</pose>
      <link name='link'>
        <collision name='col'><geometry><box><size>0.45 0.45 4.5</size></box></geometry></collision>
        <visual name='vis'>
          <geometry><box><size>0.45 0.45 4.5</size></box></geometry>
          <material>
            <script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/DarkGrey</name></script>
            <ambient>0.25 0.28 0.32 1</ambient><diffuse>0.30 0.33 0.37 1</diffuse>
          </material>
        </visual>
      </link>
    </model>""")

    return "\n".join(models)

# ==============================================================================
# GÔNDOLAS INDUSTRIAIS (RACKS DE ARMAZENAGEM COM PALLETS E CAIXAS)
# ==============================================================================
def create_storage_rack(name, x, y, yaw=0.0):
    """
    Gera uma gondola industrial porta-paletes:
    - Comprimento: 2.60m, Profundidade: 0.90m, Altura: 3.20m.
    - 4 Pilares verticais metalicos cor de seguranca (Laranja Industrial: #E65100).
    - 3 Niveis de prateleiras horizontais (vigas de aco #37474F).
    - Cargas: Pallets de madeira com caixas de papelao e containers plasticos.
    """
    length = 2.60  # Comprimento (2.6m)
    depth = 0.90   # Profundidade (0.9m)
    height = 3.20  # Altura (3.2m)
    
    xml = f"""    <!-- Gondola Industrial Porta-Paletes: {name} -->
    <model name='{name}'>
      <static>1</static>
      <pose>{x:.4f} {y:.4f} 0.0 0 0 {yaw:.6f}</pose>
      <link name='link'>
        <!-- Colisao da Base Estrutural para Evitar Colisoes do Robo -->
        <collision name='col_base'>
          <pose>0 0 {height/2:.2f} 0 0 0</pose>
          <geometry><box><size>{length:.2f} {depth:.2f} {height:.2f}</size></box></geometry>
        </collision>

        <!-- Pilares Verticais Metalicos (Laranja Industrial) -->
        <visual name='pilar_fl'>
          <pose>{-length/2 + 0.05:.2f} {depth/2 - 0.05:.2f} {height/2:.2f} 0 0 0</pose>
          <geometry><box><size>0.10 0.10 {height:.2f}</size></box></geometry>
          <material><ambient>0.90 0.35 0.05 1</ambient><diffuse>0.90 0.35 0.05 1</diffuse></material>
        </visual>
        <visual name='pilar_fr'>
          <pose>{length/2 - 0.05:.2f} {depth/2 - 0.05:.2f} {height/2:.2f} 0 0 0</pose>
          <geometry><box><size>0.10 0.10 {height:.2f}</size></box></geometry>
          <material><ambient>0.90 0.35 0.05 1</ambient><diffuse>0.90 0.35 0.05 1</diffuse></material>
        </visual>
        <visual name='pilar_bl'>
          <pose>{-length/2 + 0.05:.2f} {-depth/2 + 0.05:.2f} {height/2:.2f} 0 0 0</pose>
          <geometry><box><size>0.10 0.10 {height:.2f}</size></box></geometry>
          <material><ambient>0.90 0.35 0.05 1</ambient><diffuse>0.90 0.35 0.05 1</diffuse></material>
        </visual>
        <visual name='pilar_br'>
          <pose>{length/2 - 0.05:.2f} {-depth/2 + 0.05:.2f} {height/2:.2f} 0 0 0</pose>
          <geometry><box><size>0.10 0.10 {height:.2f}</size></box></geometry>
          <material><ambient>0.90 0.35 0.05 1</ambient><diffuse>0.90 0.35 0.05 1</diffuse></material>
        </visual>

        <!-- Vigas Horizontais das Prateleiras (Nivel 1: 0.8m, Nivel 2: 1.8m, Nivel 3: 2.8m) -->
        <visual name='prateleira_1'>
          <pose>0 0 0.80 0 0 0</pose>
          <geometry><box><size>{length:.2f} {depth:.2f} 0.06</size></box></geometry>
          <material><ambient>0.22 0.28 0.33 1</ambient><diffuse>0.22 0.28 0.33 1</diffuse></material>
        </visual>
        <visual name='prateleira_2'>
          <pose>0 0 1.80 0 0 0</pose>
          <geometry><box><size>{length:.2f} {depth:.2f} 0.06</size></box></geometry>
          <material><ambient>0.22 0.28 0.33 1</ambient><diffuse>0.22 0.28 0.33 1</diffuse></material>
        </visual>
        <visual name='prateleira_3'>
          <pose>0 0 2.80 0 0 0</pose>
          <geometry><box><size>{length:.2f} {depth:.2f} 0.06</size></box></geometry>
          <material><ambient>0.22 0.28 0.33 1</ambient><diffuse>0.22 0.28 0.33 1</diffuse></material>
        </visual>

        <!-- Cargas: Pallets de Madeira e Caixas de Papelao no Nivel 1 -->
        <visual name='pallet_l1_a'>
          <pose>{-length/4:.2f} 0 0.88 0 0 0</pose>
          <geometry><box><size>1.10 0.75 0.12</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/WoodPallet</name></script></material>
        </visual>
        <visual name='caixa_l1_a'>
          <pose>{-length/4:.2f} 0 1.25 0 0 0</pose>
          <geometry><box><size>0.95 0.70 0.60</size></box></geometry>
          <material><ambient>0.78 0.58 0.38 1</ambient><diffuse>0.78 0.58 0.38 1</diffuse></material>
        </visual>

        <visual name='pallet_l1_b'>
          <pose>{length/4:.2f} 0 0.88 0 0 0</pose>
          <geometry><box><size>1.10 0.75 0.12</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/WoodPallet</name></script></material>
        </visual>
        <visual name='container_l1_b'>
          <pose>{length/4:.2f} 0 1.25 0 0 0</pose>
          <geometry><box><size>1.00 0.70 0.55</size></box></geometry>
          <material><ambient>0.10 0.40 0.75 1</ambient><diffuse>0.10 0.40 0.75 1</diffuse></material>
        </visual>

        <!-- Cargas no Nivel 2 -->
        <visual name='pallet_l2_a'>
          <pose>{-length/4:.2f} 0 1.88 0 0 0</pose>
          <geometry><box><size>1.10 0.75 0.12</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/WoodPallet</name></script></material>
        </visual>
        <visual name='caixa_l2_a'>
          <pose>{-length/4:.2f} 0 2.25 0 0 0</pose>
          <geometry><box><size>0.90 0.65 0.60</size></box></geometry>
          <material><ambient>0.72 0.52 0.32 1</ambient><diffuse>0.72 0.52 0.32 1</diffuse></material>
        </visual>

        <visual name='pallet_l2_b'>
          <pose>{length/4:.2f} 0 1.88 0 0 0</pose>
          <geometry><box><size>1.10 0.75 0.12</size></box></geometry>
          <material><script><uri>file://media/materials/scripts/gazebo.material</uri><name>Gazebo/WoodPallet</name></script></material>
        </visual>
        <visual name='caixa_l2_b'>
          <pose>{length/4:.2f} 0 2.25 0 0 0</pose>
          <geometry><box><size>1.00 0.68 0.60</size></box></geometry>
          <material><ambient>0.80 0.60 0.40 1</ambient><diffuse>0.80 0.60 0.40 1</diffuse></material>
        </visual>
      </link>
    </model>"""
    return xml

def generate_warehouse_racks():
    """Posiciona 4 blocos de gondolas formando corredores de armazenamento."""
    racks = []
    # Setor A (Oeste / Estoque Inbound):
    racks.append(create_storage_rack('gondola_setor_a_norte', -2.10,  1.50, 0.0))
    racks.append(create_storage_rack('gondola_setor_a_sul',   -2.10, -1.50, 0.0))

    # Setor B (Leste / Estoque Outbound):
    racks.append(create_storage_rack('gondola_setor_b_norte',  2.10,  1.50, 0.0))
    racks.append(create_storage_rack('gondola_setor_b_sul',    2.10, -1.50, 0.0))

    return "\n\n".join(racks)

# ==============================================================================
# MARCADORES DE CORES PARA CORRELAÇÃO DE ODOMETRIA E ESTAÇÕES
# ==============================================================================
def generate_color_markers():
    """
    Faixas coloridas transversais sobre a linha preta (z = 0.002, 0.80m x 0.40m).
    Ao passar por cima, a camera frontal/inferior enxerga nitidamente a cor.
    """
    markers_info = [
        # (Nome, Cor_SDF, Hex_RGB, x, y, yaw, Descricao)
        ('marker_estacao_1_verde', 'Gazebo/Green', (0.0, 0.90, 0.30), -2.40, 3.00, 0.0,
         'Estacao 1: Doca de Entrada / Abastecimento (Spawn Inicial)'),
         
        ('marker_estacao_2_azul', 'Gazebo/Blue', (0.15, 0.45, 1.0), 4.20, 1.20, -math.pi/2,
         'Estacao 2: Corredor de Estoque A (Picking A)'),
         
        ('marker_estacao_3_ciano', 'Gazebo/Turquoise', (0.0, 0.85, 0.95), 0.00, 0.00, 0.0,
         'Estacao 3: Intersecao Central / Bypass'),
         
        ('marker_estacao_4_amarelo', 'Gazebo/Yellow', (1.0, 0.90, 0.0), 0.00, -3.00, math.pi,
         'Estacao 4: Corredor de Estoque B (Picking B)'),
         
        ('marker_estacao_5_vermelho', 'Gazebo/Red', (1.0, 0.10, 0.15), -4.20, -0.60, math.pi/2,
         'Estacao 5: Doca de Expedicao / Descarga Final'),
    ]

    xml_markers = []
    for name, mat_name, rgb, x, y, yaw, desc in markers_info:
        r, g, b = rgb
        xml = f"""    <!-- {desc} -->
    <model name='{name}'>
      <static>1</static>
      <pose>{x:.4f} {y:.4f} 0.002 0 0 {yaw:.6f}</pose>
      <link name='link'>
        <visual name='visual_marker'>
          <cast_shadows>0</cast_shadows>
          <geometry><box><size>0.80 0.40 0.002</size></box></geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>{mat_name}</name>
            </script>
            <ambient>{r:.2f} {g:.2f} {b:.2f} 1</ambient>
            <diffuse>{r:.2f} {g:.2f} {b:.2f} 1</diffuse>
            <emissive>{r*0.25:.2f} {g*0.25:.2f} {b*0.25:.2f} 1</emissive>
          </material>
        </visual>
      </link>
    </model>"""
        xml_markers.append(xml)

    return "\n\n".join(xml_markers)

# ==============================================================================
# CIRCUITO CÍCLICO DE LINHAS FECHADO (TILES MODULARES ESCALADOS 4.0X)
# ==============================================================================
def generate_cyclic_track_tiles():
    """
    Gera o circuito fechado (closed-loop) que passa pelos corredores do armazem:
    - Linha Norte: Y = 3.00 (tiles em Y = 3.60, yaw = 0.0)
    - Linha Leste: X = 4.20 (tiles em X = 4.80, yaw = -pi/2)
    - Linha Sul: Y = -3.00 (tiles em Y = -3.60, yaw = pi)
    - Linha Oeste: X = -4.20 (tiles em X = -4.80, yaw = pi/2)
    - Corredor Central: Y = 0.00 (tiles em Y = 0.60, yaw = 0.0)
    """
    tiles = []

    # 1. RETA NORTE (Inbound Receiving / Doca de Entrada): linha em Y = 3.00
    # X de -3.60 ate +2.40 (6 tiles retos)
    for idx, x in enumerate([-3.60, -2.40, -1.20, 0.00, 1.20, 2.40], start=1):
        tiles.append((f'tile_norte_{idx}', 'tile-reta', [x, 3.60, 0.001, 0, 0, 0.0]))

    # Curva Canto Superior Direito (TR: de (2.40, 3.00) descendo para (4.20, 2.40))
    tiles.append(('tile_curva_tr', 'tile-curva', [3.60, 3.60, 0.001, 0, 0, 0.0]))

    # 2. RETA LESTE (Aisle Leste / Outbound): linha em X = 4.20
    # Y de +2.40 ate -1.20 (4 tiles retos descendo)
    for idx, y in enumerate([2.40, 1.20, 0.00, -1.20], start=1):
        tiles.append((f'tile_leste_{idx}', 'tile-reta', [4.80, y, 0.001, 0, 0, -math.pi/2]))

    # Curva Canto Inferior Direito (BR: de (4.20, -1.20) virando para (3.60, -3.00))
    tiles.append(('tile_curva_br', 'tile-curva', [4.80, -2.40, 0.001, 0, 0, -math.pi/2]))

    # 3. RETA SUL (Outbound Shipping / Retorno): linha em Y = -3.00
    # X de +3.60 ate -2.40 (6 tiles retos indo para a esquerda)
    for idx, x in enumerate([3.60, 2.40, 1.20, 0.00, -1.20, -2.40], start=1):
        tiles.append((f'tile_sul_{idx}', 'tile-reta', [x, -3.60, 0.001, 0, 0, math.pi]))

    # Curva Canto Inferior Esquerdo (BL: de (-2.40, -3.00) subindo para (-4.20, -2.40))
    tiles.append(('tile_curva_bl', 'tile-curva', [-3.60, -3.60, 0.001, 0, 0, math.pi]))

    # 4. RETA OESTE (Aisle Oeste / Retorno Doca de Entrada): linha em X = -4.20
    # Y de -2.40 ate +1.20 (4 tiles retos subindo)
    for idx, y in enumerate([-2.40, -1.20, 0.00, 1.20], start=1):
        tiles.append((f'tile_oeste_{idx}', 'tile-reta', [-4.80, y, 0.001, 0, 0, math.pi/2]))

    # Curva Canto Superior Esquerdo (TL: de (-4.20, 1.20) virando para (-3.60, 3.00))
    tiles.append(('tile_curva_tl', 'tile-curva', [-4.80, 2.40, 0.001, 0, 0, math.pi/2]))

    # 5. CORREDOR CENTRAL DE PICKING / BYPASS (Linha em Y = 0.00)
    for idx, x in enumerate([-3.60, -2.40, -1.20, 0.00, 1.20, 2.40, 3.60], start=1):
        tiles.append((f'tile_centro_{idx}', 'tile-reta', [x, 0.60, 0.001, 0, 0, 0.0]))

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

    return "\n\n".join(models_xml)

# ==============================================================================
# MONTAGEM FINAL DO ARQUIVO .WORLD
# ==============================================================================
def build_warehouse_world():
    header = create_world_header()
    structure = generate_warehouse_structure()
    racks = generate_warehouse_racks()
    markers = generate_color_markers()
    track = generate_cyclic_track_tiles()

    footer = """
    <!-- Posicao Inicial da Camera do Operador no Gazebo (Vista Superior Isometrica) -->
    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose>0.0 -8.5 11.5 0 0.85 1.5708</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>"""

    world_content = f"""{header}

{structure}

{racks}

{markers}

{track}

{footer}
"""
    return world_content


def main():
    print("Gerando Mundo de Armazem Fabril: armazem_logistico.world...")
    content = build_warehouse_world()
    
    out_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'articubot_one', 'worlds', 'armazem_logistico.world')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'worlds', 'armazem_logistico.world'))
    ]
    
    for path in out_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f" -> Arquivo gerado com sucesso: {path}")

    print("[CONCLUIDO] Mundo de armazem logistico gerado com sucesso!")


if __name__ == '__main__':
    main()
