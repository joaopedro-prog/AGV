import math
import os
import xml.etree.ElementTree as ET

"""
Gerador de Pista 3D Multinível para o Gazebo
- Rampas de subida e descida suaves (slope ~8.5 graus)
- Viaduto / Ponte elevada a Z = 0.18m (18 cm de vão livre, o robô tem 13 cm de altura)
- Cruzamento 3D: a pista superior cruza a 90 graus por cima da pista térrea!
- Pilares de sustentação cilíndricos na ponte
- Iluminação natural suave e realista (céu azul, sol angulado, sombras suaves, sem ofuscamento)
"""

# Let's define the circuit precisely.
# We will construct a 2D/3D graph of tiles.
# Each tile has:
#   name: str
#   model_type: 'tile-reta' | 'tile-curva'
#   x, y, z: float
#   roll, pitch, yaw: float

tiles = []

def add_tile(name, model_type, x, y, z, r, p, yaw):
    tiles.append({
        'name': name,
        'model': model_type,
        'x': x, 'y': y, 'z': z,
        'r': r, 'p': p, 'yaw': yaw
    })

# Circuit Architecture:
# -------------------------------------------------------------
# 1. GROUND STRAIGHTAWAY (TÚNEL / VÃO INFERIOR)
# Crossing point is at (0.0, 0.0, 0.001) where the ground track goes along +X.
# Overpass crosses at (0.0, 0.0, 0.180) along +Y.
#
# Ground straight (under bridge):
# Tile G1: from (-0.60, 0.0) to (-0.30, 0.0)
# Tile G2: from (-0.30, 0.0) to (0.0, 0.0)  <-- UNDER THE BRIDGE!
# Tile G3: from (0.0, 0.0) to (0.30, 0.0)
# Tile G4: from (0.30, 0.0) to (0.60, 0.0)
#
# 2. TURN TO RETURN ON GROUND:
# Curve G_TR: turns from +X to -Y. Starts at (0.60, 0.0), ends at (0.75, -0.15).
# Straight G_R: from (0.75, -0.15) to (0.75, -0.45).
# Curve G_BR: turns from -Y to -X. Starts at (0.75, -0.45), ends at (0.60, -0.60).
# Straight G_B1: from (0.60, -0.60) to (0.30, -0.60).
# Straight G_B2: from (0.30, -0.60) to (0.0, -0.60).
# Straight G_B3: from (0.0, -0.60) to (-0.30, -0.60).
# Straight G_B4: from (-0.30, -0.60) to (-0.60, -0.60).
# Curve G_BL: turns from -X to +Y. Starts at (-0.60, -0.60), ends at (-0.75, -0.45).
# Straight G_L1: from (-0.75, -0.45) to (-0.75, -0.15).
#
# 3. RAMP UP TO ELEVATED DECK:
# Starts at (-0.75, -0.15, 0.001) heading +Y.
# Ramp Tile 1 (Ramp_Up_1): from Y = -0.15 to Y = +0.15, rises from Z = 0.001 to Z = 0.090 (slope ~17 deg).
# Ramp Tile 2 (Ramp_Up_2): from Y = +0.15 to Y = +0.45, rises from Z = 0.090 to Z = 0.180.
#
# 4. ELEVATED UPPER DECK (Z = 0.180m):
# Straight E_L: from (-0.75, 0.45) to (-0.75, 0.75) at Z = 0.180.
# Curve E_TL: turns from +Y to +X (RIGHT turn). Starts at (-0.75, 0.75), ends at (-0.60, 0.90) at Z = 0.180.
# Straight E_T1: from (-0.60, 0.90) to (-0.30, 0.90) at Z = 0.180.
# Straight E_T2: from (-0.30, 0.90) to (0.0, 0.90) at Z = 0.180.
# Curve E_TR: turns from +X to -Y (RIGHT turn). Starts at (0.0, 0.90), ends at (0.15, 0.75) at Z = 0.180.
# Straight E_Bridge_App: from (0.15, 0.75) to (0.15, 0.45) at Z = 0.180.
# Straight E_Bridge_Mid: from (0.15, 0.45) to (0.15, 0.15) at Z = 0.180.
# Straight E_Bridge_Cross: from (0.15, 0.15) to (0.15, -0.15) at Z = 0.180.  <-- CROSSES OVER GROUND TRACK G2!
#
# 5. RAMP DOWN BACK TO GROUND:
# After the bridge at (0.15, -0.15, 0.180) heading -Y:
# Curve E_BR: turns from -Y to -X. Starts at (0.15, -0.15), ends at (0.0, -0.30) at Z = 0.180.
# Ramp Tile 3 (Ramp_Dn_1): heading -X, from X = 0.0 to X = -0.30, drops from Z = 0.180 to Z = 0.090.
# Ramp Tile 4 (Ramp_Dn_2): heading -X, from X = -0.30 to X = -0.60, drops from Z = 0.090 to Z = 0.001.
#
# 6. RETURN TO START:
# At (-0.60, -0.30, 0.001) heading -X:
# Curve Ret_1: turns from -X to +Y. Starts at (-0.60, -0.30), ends at (-0.75, -0.15)...
# Wait! Let's verify continuity with exact math!

print('Computing precise tile poses...')
