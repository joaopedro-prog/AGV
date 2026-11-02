path = 'src/articubot_one/description/camera.xacro'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

old_header = """    <!--
      POSICIONAMENTO DA CÂMERA DO AGV
      O chassi tem comprimento de 0.335 m (termina em x = 0.335).
      Posicionamos a câmera à frente do chassi em x = 0.360 m (2.5 cm à frente do para-choque),
      centralizada em y = 0.0 m, na altura z = 0.120 m.
      A câmera é inclinada para baixo (pitch = 0.75 rad ~ 43 graus), apontando diretamente para o chão
      à frente do robô (de 15 cm a 90 cm de distância), com visão 100% livre do chassi e das rodas!
    -->
    <joint name="camera_joint" type="fixed">
        <parent link="chassis"/>
        <child link="camera_link"/>
        <origin xyz="0.210 0 0.090" rpy="0 0.52 0"/>
    </joint>"""

new_header = """    <!--
      ==========================================================================
      POSICIONAMENTO E ANGULAÇÃO DA CÂMERA DO AGV
      ==========================================================================
      Arquivo: src/articubot_one/description/camera.xacro
      Joint:   camera_joint -> <origin xyz="X Y Z" rpy="roll PITCH yaw"/>

      1. PITCH (Inclinação para cima / baixo) - Em radianos:
         - rpy="0 0.00 0" -> 0°   (Totalmente horizontal, olha para o horizonte)
         - rpy="0 0.35 0" -> 20°  (Olha suavemente para a frente e o piso distante)
         - rpy="0 0.52 0" -> 30°  (PADRÃO ATUAL: foca o chão de 15cm a 60cm à frente)
         - rpy="0 0.70 0" -> 40°  (Mais inclinada para baixo, foca de 10cm a 35cm)
         - rpy="0 0.90 0" -> 51.5°(Bem inclinada, piso próximo)
         - rpy="0 1.57 0" -> 90°  (Totalmente vertical, olhando direto pro chão)

      2. POSIÇÃO (xyz em metros):
         - X = 0.210 m (1 cm à frente do para-choque dianteiro)
         - Y = 0.000 m (Centralizada na largura)
         - Z = 0.090 m (Altura acima da base do chassi)
      ==========================================================================
    -->
    <joint name="camera_joint" type="fixed">
        <parent link="chassis"/>
        <child link="camera_link"/>
        <origin xyz="0.210 0 0.090" rpy="0 0.52 0"/>
    </joint>"""

text = text.replace(old_header, new_header)
with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated camera.xacro documentation!')
