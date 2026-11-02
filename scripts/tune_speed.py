# Update brain_params.yaml for agile, dynamic movement
path_params = 'src/agv_brain/config/brain_params.yaml'
with open(path_params, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('base_linear_speed: 0.20', 'base_linear_speed: 0.35')
text = text.replace('min_linear_speed: 0.08', 'min_linear_speed: 0.15')
text = text.replace('max_angular_speed: 1.50', 'max_angular_speed: 3.00')
text = text.replace('curve_slowdown_factor: 0.70', 'curve_slowdown_factor: 0.50')
text = text.replace('kp: 1.40', 'kp: 3.20')
text = text.replace('kd: 0.30', 'kd: 0.25')
text = text.replace('search_linear_speed: 0.04', 'search_linear_speed: 0.12')
text = text.replace('search_angular_speed: 0.55', 'search_angular_speed: 1.20')

with open(path_params, 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated brain_params.yaml speeds and gains!')
