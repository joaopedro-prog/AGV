#!/usr/bin/env python3
"""
Gerador de propriedades fisicas do AGV real a partir dos STL exportados do Fusion 360.

O que ele faz:
  1. Le os STL de src/articubot_one/meshes (exportados pelo fusion2urdf, em mm, com Y para cima).
  2. Converte para a convencao ROS (X frente, Y esquerda, Z cima) com origem no CENTRO DO EIXO
     das rodas motrizes (base_link).
  3. Calcula volume, massa (pela densidade REAL de cada material), centro de massa e tensor de
     inercia completo de cada peca, direto da malha (metodo dos tetraedros com sinal).
  4. Escreve src/articubot_one/description/robot_cad_properties.xacro, que e incluido pelo
     robot_core.xacro.

Quando usar:
  Sempre que o modelador reexportar o robo do Fusion (substitua os STL na pasta meshes/ e rode):
      python3 /workspace/scripts/gerar_propriedades_robo.py

Materiais (densidade em kg/m3):
  - base_link (chassi)                 -> Aluminio      2700
  - suportes e placas dos rodizios     -> Aluminio      2700
  - rodas motrizes (left/right)        -> Poliuretano   1200
  - rodas dos rodizios (FL/FR/BL/BR)   -> Poliuretano   1200
  - webcam (carcaca plastica)          -> ABS           1050
"""

import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, '..'))
MESH_DIR = os.path.join(WS, 'src', 'articubot_one', 'meshes')
OUT_FILE = os.path.join(WS, 'src', 'articubot_one', 'description', 'robot_cad_properties.xacro')

RHO_ALUMINIO = 2700.0
RHO_POLIURETANO = 1200.0
RHO_ABS = 1050.0

# Rotacao Fusion (Y cima) -> ROS (X frente, Y esquerda, Z cima):  x_r = -z_f ; y_r = -x_f ; z_r = y_f
M_FUSION_TO_ROS = np.array([[0.0, 0.0, -1.0],
                            [-1.0, 0.0, 0.0],
                            [0.0, 1.0, 0.0]])
# Mesma rotacao expressa em roll-pitch-yaw (URDF) para aplicar nos <visual> das malhas
MESH_RPY = (np.pi / 2.0, 0.0, -np.pi / 2.0)


def load_stl(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:5] == b'solid' and b'facet' in data[:400]:
        verts = [[float(v) for v in ln.split()[1:4]]
                 for ln in data.decode(errors='ignore').splitlines() if ln.strip().startswith('vertex')]
        tris = np.array(verts, dtype=np.float64).reshape(-1, 3, 3)
    else:
        n = struct.unpack('<I', data[80:84])[0]
        dt = np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
        tris = np.frombuffer(data[84:84 + n * 50], dtype=dt)['v'].astype(np.float64)
    return tris * 0.001  # mm -> m


def mass_props(tris, density):
    """Massa, CoM e inercia (no CoM, eixos do frame da malha) de uma malha fechada."""
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    vol_t = np.einsum('ij,ij->i', v0, np.cross(v1, v2)) / 6.0
    vol = vol_t.sum()
    com = (vol_t[:, None] * (v0 + v1 + v2) / 4.0).sum(0) / vol
    canon = np.array([[2, 1, 1], [1, 2, 1], [1, 1, 2]], dtype=np.float64) / 120.0
    A = np.stack([v0, v1, v2], axis=2)                       # (n,3,3) colunas = vertices
    cov = np.einsum('n,nij,jk,nlk->il', 6.0 * vol_t, A, canon, A)
    mass = vol * density
    cov = cov * density - mass * np.outer(com, com)
    inertia = np.trace(cov) * np.eye(3) - cov
    return vol, mass, com, inertia


def shift_inertia(I_com, mass, com, ref):
    """Teorema dos eixos paralelos: inercia no ponto ref (mesma orientacao)."""
    d = com - ref
    return I_com + mass * (np.dot(d, d) * np.eye(3) - np.outer(d, d))


def combine(parts, ref):
    """Combina varias pecas (mass, com, I_com) em um unico corpo; retorna (m, com, I_com)."""
    m = sum(p[0] for p in parts)
    com = sum(p[0] * p[1] for p in parts) / m
    I = sum(shift_inertia(p[2], p[0], p[1], com) for p in parts)
    return m, com, I


def main():
    meshes = {fn[:-4]: load_stl(os.path.join(MESH_DIR, fn))
              for fn in os.listdir(MESH_DIR) if fn.lower().endswith('.stl')}

    # ----------------------------------------------------------------------------------------
    # Origem do base_link = centro geometrico do eixo das rodas motrizes (no frame do Fusion)
    # ----------------------------------------------------------------------------------------
    lw = meshes['left_wheel1_1'].reshape(-1, 3)
    rw = meshes['right_wheel_1'].reshape(-1, 3)
    axle_f = np.array([0.0, (lw[:, 1].min() + lw[:, 1].max()) / 2.0, (lw[:, 2].min() + lw[:, 2].max()) / 2.0])

    def to_ros(tris):
        return (tris - axle_f) @ M_FUSION_TO_ROS.T

    ros = {k: to_ros(v) for k, v in meshes.items()}
    mesh_offset = M_FUSION_TO_ROS @ (-axle_f)   # xyz do <visual> das malhas no frame base_link

    # Validacao do metodo: aco no frame do Fusion deve bater com o URDF exportado (26.74 kg)
    _, m_steel, _, _ = mass_props(meshes['base_link'], 7850.0)

    out = {}
    # Chassi
    vol, m, com, I = mass_props(ros['base_link'], RHO_ALUMINIO)
    pts = ros['base_link'].reshape(-1, 3)
    out['chassis'] = dict(vol=vol, m=m, com=com, I=I)
    chassis_min, chassis_max = pts.min(0), pts.max(0)

    # Rodas motrizes
    wheels = {}
    for side, key in (('left', 'left_wheel1_1'), ('right', 'right_wheel_1')):
        p = ros[key].reshape(-1, 3)
        center = (p.min(0) + p.max(0)) / 2.0
        radius = (p[:, 2].max() - p[:, 2].min()) / 2.0
        width = p[:, 1].max() - p[:, 1].min()
        vol, m, com, I = mass_props(ros[key], RHO_POLIURETANO)
        wheels[side] = dict(center=center, radius=radius, width=width, vol=vol, m=m, com=com - center, I=I)

    wheel_radius = (wheels['left']['radius'] + wheels['right']['radius']) / 2.0
    wheel_sep = wheels['left']['center'][1] - wheels['right']['center'][1]
    ground_z = -wheel_radius

    # Rodizios (casters): placa + suporte (aluminio) + roda (poliuretano)
    casters = {}
    for c in ('FL', 'FR', 'BL', 'BR'):
        wheel_t = ros[f'{c}_wheel_1']
        wp = wheel_t.reshape(-1, 3)
        w_center = (wp.min(0) + wp.max(0)) / 2.0
        w_radius = (wp[:, 2].max() - wp[:, 2].min()) / 2.0
        # Correcao vertical: no CAD alguns rodizios ficaram ate ~7 mm ABAIXO das rodas motrizes.
        # Alinhamos o ponto mais baixo de cada rodizio com o solo das rodas motrizes.
        dz = ground_z - wp[:, 2].min()
        origin = np.array([w_center[0], w_center[1], ground_z + w_radius])
        parts = []
        for key, rho in ((f'{c}_wheel_plate_1', RHO_ALUMINIO), (f'{c}_wheel_support_1', RHO_ALUMINIO),
                         (f'{c}_wheel_1', RHO_POLIURETANO)):
            t = ros[key] + np.array([0.0, 0.0, dz])
            _, m, com, I = mass_props(t, rho)
            parts.append((m, com, I))
        m, com, I = combine(parts, origin)
        casters[c] = dict(origin=origin, dz=dz, radius=w_radius, m=m, com=com - origin, I=I)

    # Webcam (camera USB) - lente apontando para baixo pela janela do assoalho
    wc = ros['Webcam_1'].reshape(-1, 3)
    wc_min, wc_max = wc.min(0), wc.max(0)
    lens = np.array([(wc_min[0] + wc_max[0]) / 2.0, (wc_min[1] + wc_max[1]) / 2.0, wc_min[2]])
    vol, m, com, I = mass_props(ros['Webcam_1'], RHO_ABS)
    webcam = dict(m=m, com=com - lens, I=I, lens=lens)

    # ----------------------------------------------------------------------------------------
    # Escrita do xacro
    # ----------------------------------------------------------------------------------------
    f = lambda v: f'{v:.6f}'
    fv = lambda v: ' '.join(f(x) for x in v)

    def inertia_tag(I):
        return (f'ixx="{I[0,0]:.6e}" ixy="{I[0,1]:.6e}" ixz="{I[0,2]:.6e}" '
                f'iyy="{I[1,1]:.6e}" iyz="{I[1,2]:.6e}" izz="{I[2,2]:.6e}"')

    total = out['chassis']['m'] + wheels['left']['m'] + wheels['right']['m'] + \
        sum(c['m'] for c in casters.values()) + webcam['m']

    L = []
    L.append('<?xml version="1.0"?>')
    L.append('<!--')
    L.append('  ARQUIVO GERADO AUTOMATICAMENTE por scripts/gerar_propriedades_robo.py  (NAO edite a mao)')
    L.append('  Fonte: STL do Fusion 360 em src/articubot_one/meshes/')
    L.append('  Massas calculadas pelo VOLUME REAL de cada malha x densidade do material:')
    L.append(f'    Chassi (aluminio 2700 kg/m3)          : {out["chassis"]["vol"]*1e6:8.1f} cm3 -> {out["chassis"]["m"]:.3f} kg')
    L.append(f'    Roda esquerda (poliuretano 1200 kg/m3): {wheels["left"]["vol"]*1e6:8.1f} cm3 -> {wheels["left"]["m"]:.3f} kg')
    L.append(f'    Roda direita  (poliuretano 1200 kg/m3): {wheels["right"]["vol"]*1e6:8.1f} cm3 -> {wheels["right"]["m"]:.3f} kg')
    for k, c in casters.items():
        L.append(f'    Rodizio {k} (placa+suporte Al, roda PU) : {c["m"]*1000:7.1f} g   (correcao vertical {c["dz"]*1000:+.1f} mm)')
    L.append(f'    Webcam (ABS 1050 kg/m3)               : {webcam["m"]*1000:7.1f} g')
    L.append(f'    TOTAL ESTRUTURA                       : {total:.3f} kg   (Fusion com aco dava {m_steel:.2f} kg so no chassi)')
    L.append('  Frame base_link = centro do eixo das rodas motrizes (X frente, Y esquerda, Z cima).')
    L.append('-->')
    L.append('<robot xmlns:xacro="http://www.ros.org/wiki/xacro">')
    L.append('')
    L.append('    <!-- Transformacao das malhas do Fusion (Y para cima, mm) para o frame base_link -->')
    L.append(f'    <xacro:property name="cad_mesh_rpy" value="{fv(MESH_RPY)}"/>')
    L.append(f'    <xacro:property name="cad_mesh_xyz" value="{fv(mesh_offset)}"/>')
    L.append(f'    <xacro:property name="cad_mesh_x" value="{f(mesh_offset[0])}"/>')
    L.append(f'    <xacro:property name="cad_mesh_y" value="{f(mesh_offset[1])}"/>')
    L.append(f'    <xacro:property name="cad_mesh_z" value="{f(mesh_offset[2])}"/>')
    L.append('')
    L.append('    <!-- Dimensoes principais medidas nas malhas -->')
    L.append(f'    <xacro:property name="wheel_radius" value="{f(wheel_radius)}"/>')
    L.append(f'    <xacro:property name="wheel_thickness" value="{f(wheels["left"]["width"])}"/>')
    L.append(f'    <xacro:property name="wheel_separation" value="{f(wheel_sep)}"/>')
    L.append(f'    <xacro:property name="wheel_offset_y" value="{f(wheel_sep / 2.0)}"/>')
    L.append(f'    <xacro:property name="chassis_min_x" value="{f(chassis_min[0])}"/>')
    L.append(f'    <xacro:property name="chassis_max_x" value="{f(chassis_max[0])}"/>')
    L.append(f'    <xacro:property name="chassis_half_width" value="{f(chassis_max[1])}"/>')
    L.append(f'    <xacro:property name="chassis_bottom_z" value="{f(chassis_min[2])}"/>')
    L.append(f'    <xacro:property name="chassis_top_z" value="{f(chassis_max[2])}"/>')
    L.append('')
    L.append('    <!-- Chassi (aluminio) -->')
    c = out['chassis']
    L.append(f'    <xacro:property name="chassis_mass" value="{f(c["m"])}"/>')
    L.append(f'    <xacro:property name="chassis_com" value="{fv(c["com"])}"/>')
    L.append('    <xacro:macro name="chassis_inertia">')
    L.append(f'        <inertia {inertia_tag(c["I"])}/>')
    L.append('    </xacro:macro>')
    L.append('')
    for side in ('left', 'right'):
        w = wheels[side]
        L.append(f'    <!-- Roda motriz {side} (poliuretano) - centro em {fv(w["center"])} -->')
        L.append(f'    <xacro:property name="{side}_wheel_mass" value="{f(w["m"])}"/>')
        L.append(f'    <xacro:property name="{side}_wheel_center_y" value="{f(w["center"][1])}"/>')
        L.append(f'    <xacro:property name="{side}_wheel_com" value="{fv(w["com"])}"/>')
        L.append(f'    <xacro:macro name="{side}_wheel_inertia">')
        L.append(f'        <inertia {inertia_tag(w["I"])}/>')
        L.append('    </xacro:macro>')
        L.append('')
    for k, cc in casters.items():
        L.append(f'    <!-- Rodizio {k}: placa + suporte (aluminio) + roda (poliuretano) -->')
        L.append(f'    <xacro:property name="caster_{k}_xyz" value="{fv(cc["origin"])}"/>')
        L.append(f'    <xacro:property name="caster_{k}_dz" value="{f(cc["dz"])}"/>')
        L.append(f'    <xacro:property name="caster_{k}_radius" value="{f(cc["radius"])}"/>')
        L.append(f'    <xacro:property name="caster_{k}_mass" value="{f(cc["m"])}"/>')
        L.append(f'    <xacro:property name="caster_{k}_com" value="{fv(cc["com"])}"/>')
        L.append(f'    <xacro:macro name="caster_{k}_inertia">')
        L.append(f'        <inertia {inertia_tag(cc["I"])}/>')
        L.append('    </xacro:macro>')
        L.append('')
    L.append('    <!-- Webcam (ABS) - lente = centro da face inferior (olha para o piso) -->')
    L.append(f'    <xacro:property name="webcam_lens_xyz" value="{fv(webcam["lens"])}"/>')
    L.append(f'    <xacro:property name="webcam_lens_x" value="{f(webcam["lens"][0])}"/>')
    L.append(f'    <xacro:property name="webcam_lens_z" value="{f(webcam["lens"][2])}"/>')
    L.append(f'    <xacro:property name="webcam_mass" value="{f(webcam["m"])}"/>')
    L.append(f'    <xacro:property name="webcam_com" value="{fv(webcam["com"])}"/>')
    L.append('    <xacro:macro name="webcam_inertia">')
    L.append(f'        <inertia {inertia_tag(webcam["I"])}/>')
    L.append('    </xacro:macro>')
    L.append('')
    L.append('</robot>')

    with open(OUT_FILE, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(L) + '\n')

    print(f'[OK] Gerado: {OUT_FILE}')
    print(f'  Validacao (aco, frame Fusion): chassi = {m_steel:.3f} kg (URDF do Fusion: 26.738 kg)')
    print(f'  Chassi aluminio: {out["chassis"]["m"]:.3f} kg | Rodas PU: {wheels["left"]["m"]:.3f} / {wheels["right"]["m"]:.3f} kg')
    print(f'  Raio roda: {wheel_radius*1000:.1f} mm | Bitola (separacao): {wheel_sep*1000:.1f} mm | Largura roda: {wheels["left"]["width"]*1000:.1f} mm')
    print(f'  Chassi X[{chassis_min[0]:.3f}, {chassis_max[0]:.3f}]  meia-largura {chassis_max[1]:.3f}  Z[{chassis_min[2]:.3f}, {chassis_max[2]:.3f}] (rel. eixo)')
    print(f'  Lente webcam (rel. eixo): {np.round(webcam["lens"], 4)}  -> altura do solo {webcam["lens"][2] + wheel_radius:.4f} m')
    for k, cc in casters.items():
        print(f'  Rodizio {k}: pos {np.round(cc["origin"], 4)}  correcao {cc["dz"]*1000:+.1f} mm  massa {cc["m"]*1000:.1f} g')
    print(f'  MASSA TOTAL: {total:.3f} kg')


if __name__ == '__main__':
    sys.exit(main())
