# Update launch_sim.launch.py
path = 'src/articubot_one/launch/launch_sim.launch.py'
with open(path, 'r', encoding='utf-8') as f:
    t = f.read()

old_spawn_block = """    # Ajusta o spawn padrão sobre a linha conforme o mundo se não houver coordenadas customizadas
    if 'circle' in resolved_world.lower() and spawn_x_val == '0.05' and spawn_y_val == '-0.157':
        spawn_x_val = '0.0'
        spawn_y_val = '0.30'
        spawn_z_val = '0.05'
        spawn_yaw_val = '0.0'
        print(f"[launch_sim] Posição de spawn ajustada para circle_world: x={spawn_x_val}, y={spawn_y_val}")"""

new_spawn_block = """    # Ajusta o spawn padrão sobre a linha conforme o mundo se não houver coordenadas customizadas
    rw_lower = resolved_world.lower()
    if ('pista_completa_3d' in rw_lower or '3d' in rw_lower) and spawn_x_val == '0.05' and spawn_y_val == '-0.157':
        spawn_x_val = '-0.45'
        spawn_y_val = '0.0'
        spawn_z_val = '0.05'
        spawn_yaw_val = '0.0'
        print(f"[launch_sim] Posição de spawn ajustada para pista_completa_3d: x={spawn_x_val}, y={spawn_y_val}")
    elif ('circle' in rw_lower or 'teste_8' in rw_lower or 'circuito_8' in rw_lower) and spawn_x_val == '0.05' and spawn_y_val == '-0.157':
        spawn_x_val = '0.0'
        spawn_y_val = '0.30'
        spawn_z_val = '0.05'
        spawn_yaw_val = '0.0'
        print(f"[launch_sim] Posição de spawn ajustada para circuito 8 tiles: x={spawn_x_val}, y={spawn_y_val}")"""

t = t.replace(old_spawn_block, new_spawn_block)
t = t.replace("'circuit1.world'", "'pista_completa_3d.world'")
with open(path, 'w', encoding='utf-8') as f:
    f.write(t)
print('Updated launch_sim.launch.py')

# Update default in agv_complete.launch.py
path_hw = 'src/agv_hardware/launch/agv_complete.launch.py'
with open(path_hw, 'r', encoding='utf-8') as f:
    thw = f.read()
thw = thw.replace("default_value='circuit1.world'", "default_value='pista_completa_3d.world'")
with open(path_hw, 'w', encoding='utf-8') as f:
    f.write(thw)
print('Updated agv_complete.launch.py')
