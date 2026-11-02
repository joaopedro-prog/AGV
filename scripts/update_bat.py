path = 'scripts/2_iniciar_simulacao.bat'
with open(path, 'r', encoding='latin-1') as f:
    t = f.read()
t = t.replace('(Pista Circular - 4 Curvas)', '(Circuito Fechado - 8 Tiles - 90x90cm)')
t = t.replace('wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1', 'wsl -d Ubuntu-24.04 docker start meu_container_ros >nul 2>&1\r\nwsl -d Ubuntu-24.04 docker exec meu_container_ros pkill -9 -f "gzserver|gzclient" >nul 2>&1')
with open(path, 'w', encoding='latin-1') as f:
    f.write(t)
print('Updated 2_iniciar_simulacao.bat')
