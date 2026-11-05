#!/usr/bin/env python3
"""
controlar_joystick.py
---------------------
Script de Teleoperacao de AGV via Joystick USB / Gamepad (Xbox, PS4/PS5, Generico).
Controla tanto o robo simulado (Gazebo / Docker) quanto o robo fisico real (Raspberry Pi 5 via Wi-Fi).

Destaques:
- Deteccao automatica e selecao interativa de controles USB e portas seriais conectadas.
- Opcao para minimizar o terminal automaticamente (nao atrapalha a visao da simulacao ou tela).
- Suporte a eventos em segundo plano (continua respondendo aos comandos mesmo minimizado).
- Modos Normal, Turbo (RT/RB) e Precisao (LT/LB).
- Parada de Emergencia no botao B.
- Compativel com Windows, Linux e Raspberry Pi.
"""

import os
import sys
import time
import json
import socket
import subprocess

# Permite que o SDL processe eventos de controle mesmo quando a janela nao esta em foco
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

# Suprime banner do Pygame
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

try:
    import pygame
except ImportError:
    print("\n[ERRO] A biblioteca 'pygame' nao foi encontrada!")
    print("Instale executando: pip install pygame\n")
    sys.exit(1)

# Constantes de velocidade padrao
MAX_LINEAR_NORMAL = 0.40    # m/s (~1.44 km/h)
MAX_ANGULAR_NORMAL = 1.00   # rad/s (~57 deg/s)

MAX_LINEAR_TURBO = 0.85     # m/s (~3.06 km/h)
MAX_ANGULAR_TURBO = 1.80    # rad/s (~103 deg/s)

MAX_LINEAR_SLOW = 0.15      # m/s (~0.54 km/h - modo de precisao)
MAX_ANGULAR_SLOW = 0.45     # rad/s

DEADZONE = 0.10             # Ignora pequenas variacoes no centro do analogico
LOOP_RATE_HZ = 30.0         # Taxa de envio dos comandos (30 vezes por segundo)


def get_available_com_ports():
    """Detecta portas seriais COM conectadas no Windows."""
    ports = []
    if sys.platform.startswith('win'):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM')
            for i in range(winreg.QueryInfoKey(key)[1]):
                val = winreg.EnumValue(key, i)
                ports.append((val[1], val[0]))
        except Exception:
            pass
    return ports


def set_console_title(text):
    """Atualiza o titulo da janela do console."""
    if sys.platform.startswith('win'):
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(text)
        except Exception:
            pass
    else:
        sys.stdout.write(f"\x1b]2;{text}\x07")
        sys.stdout.flush()


def minimize_console_window():
    """Minimiza a janela do console para liberar a visao da tela."""
    if sys.platform.startswith('win'):
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                # SW_MINIMIZE = 6
                ctypes.windll.user32.ShowWindow(hwnd, 6)
                return True
        except Exception:
            pass
    return False


def apply_deadzone_and_curve(value, deadzone=DEADZONE):
    """Aplica zona morta e curva exponencial suave de aceleracao."""
    if abs(value) < deadzone:
        return 0.0
    # Normaliza entre 0 e 1 apos a deadzone
    sign = 1.0 if value > 0 else -1.0
    val_norm = (abs(value) - deadzone) / (1.0 - deadzone)
    # Curva exponencial para maior precisao em velocidades baixas
    val_curved = sign * (val_norm ** 1.5)
    return max(-1.0, min(1.0, val_curved))


def scan_devices():
    """Escaneia todos os joysticks e portas USB/COM disponiveis."""
    pygame.joystick.quit()
    pygame.joystick.init()
    
    joy_count = pygame.joystick.get_count()
    joysticks = []
    for i in range(joy_count):
        try:
            j = pygame.joystick.Joystick(i)
            j.init()
            joysticks.append({
                'index': i,
                'name': j.get_name(),
                'axes': j.get_numaxes(),
                'buttons': j.get_numbuttons(),
                'hats': j.get_numhats()
            })
        except Exception:
            pass
            
    com_ports = get_available_com_ports()
    return joysticks, com_ports


def select_controller_interactive(joysticks, com_ports):
    """Permite ao usuario selecionar o controle ou optar por deteccao automatica."""
    print("=" * 70)
    print("          CONTROLE TELEOPERADO POR JOYSTICK USB - AGV")
    print("=" * 70)
    print()
    
    if not joysticks and not com_ports:
        print("[!] ATENCAO: Nenhum controle USB ou porta serial foi detectado!")
        print("    Por favor, conecte o controle USB no computador e tente novamente.")
        print()
        input("Pressione ENTER para tentar redetectar...")
        joysticks, com_ports = scan_devices()
        if not joysticks and not com_ports:
            print("[x] Nenhum controle detectado. Encerrando.")
            return None

    print("Dispositivos de Entrada Detectados:")
    for j in joysticks:
        print(f"  [Controle {j['index']}] {j['name']} ({j['axes']} Eixos, {j['buttons']} Botoes, {j['hats']} D-Pad)")
        
    for p, desc in com_ports:
        print(f"  [Serial]     {p} ({desc})")
        
    print()
    
    # Se so tem 1 joystick, opcao de deteccao automatica direta
    if len(joysticks) == 1:
        auto_joy = joysticks[0]
        escolha = input(f"Controle detectado: '{auto_joy['name']}'.\nPressione [ENTER] para DETECCAO AUTOMATICA ou digite o indice: ").strip()
        if escolha == "" or escolha == str(auto_joy['index']):
            print(f"[OK] Utilizando controle: {auto_joy['name']}")
            return auto_joy['index']
        try:
            return int(escolha)
        except ValueError:
            return auto_joy['index']
            
    # Se tem mais de um, o usuario escolhe
    while True:
        try:
            escolha = input("Digite o numero do controle que deseja utilizar [0]: ").strip()
            if escolha == "":
                return joysticks[0]['index']
            idx = int(escolha)
            if any(j['index'] == idx for j in joysticks):
                return idx
            print("[!] Indice invalido. Tente novamente.")
        except ValueError:
            print("[!] Por favor, digite um numero valido.")


def select_target():
    """Seleciona se o comando vai para a simulacao Gazebo ou para o robo real."""
    print()
    print("Destino do Comando:")
    print("  [1] Simulacao Local no Gazebo (Docker - Padrao)")
    print("  [2] Robo Real via Wi-Fi / Rede Local (Raspberry Pi 5)")
    print()
    opt = input("Escolha a opcao [1]: ").strip()
    
    if opt == "2":
        ip = input("Digite o IP do Robo Real [192.168.1.50]: ").strip()
        if not ip:
            ip = "192.168.1.50"
        return "real", ip
    else:
        return "sim", "127.0.0.1"


def main():
    pygame.init()
    pygame.joystick.init()
    
    set_console_title("AGV - Controle por Joystick USB")
    
    joysticks, com_ports = scan_devices()
    selected_joy_idx = select_controller_interactive(joysticks, com_ports)
    if selected_joy_idx is None:
        sys.exit(1)
        
    target_type, target_ip = select_target()
    
    # Inicializa o joystick escolhido
    joy = pygame.joystick.Joystick(selected_joy_idx)
    joy.init()
    joy_name = joy.get_name()
    num_axes = joy.get_numaxes()
    num_buttons = joy.get_numbuttons()
    num_hats = joy.get_numhats()
    
    print()
    print(f"[OK] Joystick ativado: {joy_name}")
    print("     - Alavanca Esquerda: Frente / Tras e Rotacao")
    print("     - Gatilho Direito (RT / RB): Modo TURBO")
    print("     - Gatilho Esquerdo (LT / LB): Modo LENTO / PRECISAO")
    print("     - Botao B: PARADA DE EMERGENCIA")
    print("     - Botao A: Liberar Parada de Emergencia")
    print("     - Botao Back / Select: Sair")
    print()

    # Perguntar sobre minimizar a janela
    min_opt = input("Deseja minimizar esta janela para nao atrapalhar a visao da tela? (S/n) [S]: ").strip().lower()
    auto_minimize = (min_opt != 'n')
    
    # Prepara o transmissor
    pipe_proc = None
    udp_sock = None
    
    if target_type == "sim":
        print("[+] Conectando com a Simulacao Docker (pipe direto /cmd_vel_joy)...")
        # Inicia o no ROS 2 receiver via docker exec -i
        cmd = [
            'docker', 'exec', '-i', 'meu_container_ros',
            '/workspace/scripts/ros_exec.sh', 'python3', '/workspace/scripts/teleop_joy_receiver.py'
        ]
        try:
            pipe_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            time.sleep(0.5)
            print("[OK] Canal de controle da simulacao estabelecido!")
        except Exception as e:
            print(f"[ERRO] Nao foi possivel iniciar no Docker: {e}")
            print("Verifique se o container 'meu_container_ros' esta em execucao.")
            sys.exit(1)
    else:
        print(f"[+] Conectando ao Robo Real via UDP ({target_ip}:9876)...")
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("[OK] Canal UDP para o robo real ativo!")

    if auto_minimize:
        print()
        print("Minimizando em 2 segundos... Pode comecar a pilotar no controle!")
        time.sleep(2.0)
        minimize_console_window()

    emergency_stop = False
    last_send_time = 0.0
    dt = 1.0 / LOOP_RATE_HZ
    
    print("\n>>> PILOTAGEM ATIVA! Pressione Ctrl+C ou o botao Back no controle para parar. <<<\n")
    
    try:
        while True:
            t0 = time.time()
            pygame.event.pump()
            
            # Checa botao Back (normalmente botao 6 no Xbox ou 8 no genérico)
            if num_buttons > 6 and joy.get_button(6):
                print("\n[INFO] Botao Back pressionado. Encerrando...")
                break
                
            # Botao B (normalmente botao 1 no Xbox) = Parada de Emergencia
            if num_buttons > 1 and joy.get_button(1):
                if not emergency_stop:
                    emergency_stop = True
                    print("\n[!] >> PARADA DE EMERGENCIA ACIONADA! (Pressione A para liberar) <<")
                    
            # Botao A (normalmente botao 0 no Xbox) = Libera Parada
            if num_buttons > 0 and joy.get_button(0):
                if emergency_stop:
                    emergency_stop = False
                    print("\n[OK] Parada de emergencia liberada. Controle normal restabelecido.")

            # Leitura dos eixos analogicos
            # Eixo 1: Alavanca esquerda vertical (para cima eh negativo no Pygame)
            raw_ly = joy.get_axis(1) if num_axes > 1 else 0.0
            # Eixo 0: Alavanca esquerda horizontal
            raw_lx = joy.get_axis(0) if num_axes > 0 else 0.0
            # Eixo 2: Alavanca direita horizontal (permite estercar com qualquer um dos sticks)
            raw_rx = joy.get_axis(2) if num_axes > 2 else 0.0
            
            # Aplica zona morta e curva
            norm_linear = apply_deadzone_and_curve(-raw_ly)
            
            # Escolhe o stick horizontal que estiver sendo movido
            turn_input = raw_rx if abs(raw_rx) > abs(raw_lx) else raw_lx
            norm_angular = apply_deadzone_and_curve(-turn_input)
            
            # D-Pad (Hat 0) para toques discretos de alinhamento fino
            if num_hats > 0:
                hat_x, hat_y = joy.get_hat(0)
                if hat_y != 0 and abs(norm_linear) < 0.01:
                    norm_linear = 0.40 if hat_y > 0 else -0.40
                if hat_x != 0 and abs(norm_angular) < 0.01:
                    norm_angular = -0.50 if hat_x > 0 else 0.50

            # Checagem de modo Turbo e Precisao
            # Triggers Xbox: Axis 5 (RT) e Axis 4 (LT) variam de -1.0 a +1.0
            is_turbo = False
            is_slow = False
            
            if num_axes >= 6:
                if joy.get_axis(5) > 0.1:  # RT pressionado
                    is_turbo = True
                if joy.get_axis(4) > 0.1:  # LT pressionado
                    is_slow = True
            
            # Suporte alternativo para botoes RB (5) e LB (4)
            if num_buttons > 5 and joy.get_button(5):
                is_turbo = True
            if num_buttons > 4 and joy.get_button(4):
                is_slow = True

            # Define limites de velocidade conforme perfil ativo
            if is_turbo:
                max_v = MAX_LINEAR_TURBO
                max_w = MAX_ANGULAR_TURBO
                mode_str = "TURBO"
            elif is_slow:
                max_v = MAX_LINEAR_SLOW
                max_w = MAX_ANGULAR_SLOW
                mode_str = "PRECISAO"
            else:
                max_v = MAX_LINEAR_NORMAL
                max_w = MAX_ANGULAR_NORMAL
                mode_str = "NORMAL"

            if emergency_stop:
                cmd_v = 0.0
                cmd_w = 0.0
                stop_flag = 1
                mode_str = "EMERGENCIA"
            else:
                cmd_v = round(norm_linear * max_v, 3)
                cmd_w = round(norm_angular * max_w, 3)
                stop_flag = 0

            # Atualiza titulo do console com telemetria ao vivo
            status_title = f"AGV Joy [{mode_str}] | V: {cmd_v:+.2f} m/s | W: {cmd_w:+.2f} rad/s | [B]=STOP [RT]=TURBO"
            set_console_title(status_title)

            # Transmissao dos comandos
            if pipe_proc and pipe_proc.stdin:
                try:
                    pipe_proc.stdin.write(f"{cmd_v},{cmd_w},{stop_flag}\n")
                    pipe_proc.stdin.flush()
                except Exception:
                    print("\n[x] Conexao com a simulacao perdida.")
                    break
            elif udp_sock:
                try:
                    payload = json.dumps({'v': cmd_v, 'w': cmd_w, 'stop': bool(stop_flag)})
                    udp_sock.sendto(payload.encode('utf-8'), (target_ip, 9876))
                except Exception:
                    pass

            elapsed = time.time() - t0
            sleep_time = max(0.001, dt - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[!] Encerrando teleoperacao por joystick...")
    finally:
        set_console_title("AGV - Controle Finalizado")
        # Envia comando de parada final
        if pipe_proc and pipe_proc.stdin:
            try:
                pipe_proc.stdin.write("0.0,0.0,1\n")
                pipe_proc.stdin.flush()
                pipe_proc.terminate()
            except Exception:
                pass
        if udp_sock:
            try:
                payload = json.dumps({'v': 0.0, 'w': 0.0, 'stop': True})
                udp_sock.sendto(payload.encode('utf-8'), (target_ip, 9876))
                udp_sock.close()
            except Exception:
                pass
        pygame.quit()
        print("[OK] Teleoperacao finalizada com seguranca. Robo parado.")


if __name__ == '__main__':
    main()
