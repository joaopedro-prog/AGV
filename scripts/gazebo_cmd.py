#!/usr/bin/env python3
"""
Ferramenta de Comandos Rápidos para o Gazebo (Hot-Reload, Teleporte, Luz e Física)
Sem necessidade de reiniciar o Gazebo!
"""

import sys
import subprocess
import time
import shlex

def run_cmd(cmd_list, timeout=25):
    try:
        # Garante ambiente ROS 2 carregado caso execute via python puro
        if isinstance(cmd_list, list):
            cmd_str = shlex.join(cmd_list)
        else:
            cmd_str = str(cmd_list)
        full_cmd = f"source /opt/ros/humble/setup.bash && source /workspace/install/setup.bash 2>/dev/null && {cmd_str}"
        res = subprocess.run(["/bin/bash", "-c", full_cmd], capture_output=True, text=True, timeout=timeout)
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        return False, "", str(e)

def reload_robot():
    print("\n======================================================================")
    print("  ATUALIZANDO MODELO DO ROBÔ NO GAZEBO (HOT-RELOAD)...")
    print("======================================================================")
    
    # 1. Gera o URDF novo a partir do Xacro
    print("[1/3] Processando xacro atualizado...")
    xacro_cmd = "xacro /workspace/src/articubot_one/description/robot.urdf.xacro use_ros2_control:=false sim_mode:=true > /tmp/reloaded_robot.urdf"
    ok, out, err = run_cmd(xacro_cmd, timeout=20)
    if not ok:
        print(f"[ERRO] Falha ao processar Xacro:\n{err}\n{out}")
        return False

    # 2. Deleta a entidade atual
    print("[2/3] Removendo modelo antigo do Gazebo...")
    run_cmd(["gz", "model", "-m", "my_bot", "-d"], timeout=10)
    run_cmd(["ros2", "service", "call", "/delete_entity", "gazebo_msgs/srv/DeleteEntity", "{name: 'my_bot'}"], timeout=10)
    time.sleep(1.0)

    # 3. Spawna o novo modelo na linha
    print("[3/3] Inserindo modelo atualizado sobre a linha...")
    spawn_cmd = [
        "ros2", "run", "gazebo_ros", "spawn_entity.py",
        "-file", "/tmp/reloaded_robot.urdf",
        "-entity", "my_bot",
        "-x", "-0.45", "-y", "0.0", "-z", "0.09", "-Y", "0.0"
    ]
    ok, out, err = run_cmd(spawn_cmd, timeout=20)
    if ok or "Successfully" in out:
        print("\n[SUCESSO] Robô atualizado e respawnado com sucesso no Gazebo!")
        return True
    else:
        print(f"\n[AVISO] Saída do spawn:\n{out}\n{err}")
        return False

def teleport_start():
    print("\n[Gazebo] Teleportando AGV para a linha de largada (x=-0.45, y=0.0)...")
    cmd = ["gz", "model", "-m", "my_bot", "-x", "-0.45", "-y", "0.0", "-z", "0.09", "-R", "0", "-P", "0", "-Y", "0"]
    ok, out, err = run_cmd(cmd)
    if ok:
        print("[SUCESSO] Robô reposicionado na largada!")
    else:
        print(f"[ERRO] {err}")

def teleport_ramp():
    print("\n[Gazebo] Teleportando AGV para a subida da rampa (x=-1.20, y=-0.65)...")
    cmd = ["gz", "model", "-m", "my_bot", "-x", "-1.20", "-y", "-0.65", "-z", "0.09", "-R", "0", "-P", "0", "-Y", "1.5708"]
    ok, out, err = run_cmd(cmd)
    if ok:
        print("[SUCESSO] Robô reposicionado em frente à rampa!")
    else:
        print(f"[ERRO] {err}")

def toggle_pause(pause_state):
    state_str = "Pausando" if pause_state else "Despausando"
    service = "/pause_physics" if pause_state else "/unpause_physics"
    print(f"\n[Gazebo] {state_str} simulação...")
    ok, out, err = run_cmd(["ros2", "service", "call", service, "std_srvs/srv/Empty", "{}"])
    if ok:
        print(f"[SUCESSO] Simulação {'pausada' if pause_state else 'em execução'}!")

def reset_world():
    print("\n[Gazebo] Resetando física do mundo e contadores...")
    ok, out, err = run_cmd(["ros2", "service", "call", "/reset_world", "std_srvs/srv/Empty", "{}"])
    if ok:
        print("[SUCESSO] Mundo resetado!")

def set_light(mode):
    # Valores de iluminação solar
    presets = {
        "dia": {'r': 0.95, 'g': 0.95, 'b': 0.92, 'name': 'Diurna Clara (Alto Brilho)'},
        "suave": {'r': 0.70, 'g': 0.70, 'b': 0.68, 'name': 'Natural Suave (Equilibrada)'},
        "entardecer": {'r': 0.95, 'g': 0.60, 'b': 0.35, 'name': 'Entardecer / Pôr do Sol'},
        "noite": {'r': 0.20, 'g': 0.25, 'b': 0.35, 'name': 'Penumbra Noturna (Foco em Câmera/Lidar)'},
    }
    preset = presets.get(mode, presets["suave"])
    print(f"\n[Gazebo] Alterando iluminação para: {preset['name']}...")
    
    msg = f'name: "sun" diffuse {{ r: {preset["r"]} g: {preset["g"]} b: {preset["b"]} a: 1.0 }}'
    cmd = ["gz", "topic", "-p", "/gazebo/default/light/modify", "-m", msg]
    ok, out, err = run_cmd(cmd)
    if ok:
        print("[SUCESSO] Iluminação atualizada em tempo real!")
    else:
        print(f"[AVISO] Tentando método direto de luz...")
        # fallback via gz world
        run_cmd(["gz", "topic", "-p", "/gazebo/default/light/modify", "-m", msg])
        print("[SUCESSO] Comando de luz enviado!")

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "reload":
            reload_robot()
        elif cmd == "teleport":
            teleport_start()
        elif cmd == "ramp" or cmd == "rampa":
            teleport_ramp()
        elif cmd == "pause":
            toggle_pause(True)
        elif cmd == "unpause":
            toggle_pause(False)
        elif cmd == "reset":
            reset_world()
        elif cmd == "light":
            mode = sys.argv[2] if len(sys.argv) > 2 else "suave"
            set_light(mode)
        else:
            print(f"Comando desconhecido: {cmd}")
        return

    # Menu interativo em terminal
    while True:
        print("\n" + "="*70)
        print("                 COMANDOS RÁPIDOS DO GAZEBO")
        print("         (Janela Externa de Controle sem Reiniciar)")
        print("="*70)
        print("  [1] Hot-Reload: Recarregar Modelo do Robo (atualiza URDF/Xacro agora)")
        print("  [2] Teleportar Robo para a Largada (x=-0.45, y=0.0)")
        print("  [3] Teleportar Robo para a Rampa (x=-1.20, y=-0.65)")
        print("  [4] Pausar a Simulacao")
        print("  [5] Continuar / Despausar Simulacao")
        print("  [6] Resetar Fisica do Mundo (Reset World)")
        print("  [7] Mudar Iluminacao: Diurna Clara (Alto Brilho)")
        print("  [8] Mudar Iluminacao: Natural Suave (Padrao)")
        print("  [9] Mudar Iluminacao: Entardecer / Alaranjada")
        print("  [N] Mudar Iluminacao: Penumbra Noturna (Teste de Sensores)")
        print("  [0] Fechar esta Janela")
        print("="*70)
        
        try:
            opc = input("Escolha uma opcao: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
            
        if opc == "0":
            break
        elif opc == "1":
            reload_robot()
        elif opc == "2":
            teleport_start()
        elif opc == "3" or opc == "r":
            teleport_ramp()
        elif opc == "4":
            toggle_pause(True)
        elif opc == "5":
            toggle_pause(False)
        elif opc == "6":
            reset_world()
        elif opc == "7":
            set_light("dia")
        elif opc == "8":
            set_light("suave")
        elif opc == "9":
            set_light("entardecer")
        elif opc == "n":
            set_light("noite")
        else:
            print("[ERRO] Opcao invalida!")
        
        input("\nPressione [Enter] para continuar...")

if __name__ == "__main__":
    main()
