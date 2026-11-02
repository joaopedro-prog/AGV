# 1. Update brain_params.yaml
path_bp = 'src/agv_brain/config/brain_params.yaml'
with open(path_bp, 'r', encoding='utf-8') as f:
    bp = f.read()
bp = bp.replace('auto_start: true', 'auto_start: false')
with open(path_bp, 'w', encoding='utf-8') as f:
    f.write(bp)
print('Updated brain_params.yaml: auto_start: false')

# 2. Update agv_complete.launch.py
path_ac = 'src/agv_hardware/launch/agv_complete.launch.py'
with open(path_ac, 'r', encoding='utf-8') as f:
    ac = f.read()
ac = ac.replace("default_value='true',\n            description='Se true, inicia seguindo linha", "default_value='false',\n            description='Se true, inicia seguindo linha")
ac = ac.replace("default_value='true',\r\n            description='Se true, inicia seguindo linha", "default_value='false',\r\n            description='Se true, inicia seguindo linha")
with open(path_ac, 'w', encoding='utf-8') as f:
    f.write(ac)
print('Updated agv_complete.launch.py: auto_start: false')

# 3. Update brain.launch.py
path_bl = 'src/agv_brain/launch/brain.launch.py'
with open(path_bl, 'r', encoding='utf-8') as f:
    bl = f.read()
bl = bl.replace("default_value='true',\n            description='Se true, comeca a seguir linha", "default_value='false',\n            description='Se true, comeca a seguir linha")
bl = bl.replace("default_value='true',\r\n            description='Se true, comeca a seguir linha", "default_value='false',\r\n            description='Se true, comeca a seguir linha")
with open(path_bl, 'w', encoding='utf-8') as f:
    f.write(bl)
print('Updated brain.launch.py: auto_start: false')
