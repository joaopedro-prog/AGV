#!/usr/bin/env python3
"""
agv_beacon.py — Serviço leve de descoberta automática na LAN (estilo FRC roboRIO).

Escuta pacotes broadcast UDP na porta 5800 (faixa padrão FRC 5800-5810) com
payload iniciando por "AGV_DISCOVER" e responde com os metadados do robô
(hostname, porta Web, usuário SSH, uptime e deploy_info.json).
"""

import json
import os
import signal
import socket
import sys
import time

BEACON_PORT = int(os.environ.get('AGV_BEACON_PORT', '5800'))
WEB_PORT = int(os.environ.get('WEB_PORT', '8080'))
SSH_USER = os.environ.get('AGV_SSH_USER', 'agv')
DEPLOY_INFO_PATHS = (
    '/workspace/src/agv_dashboard/agv_dashboard/static/deploy_info.json',
    '/workspace/deploy_info.json',
)
START_TIME = time.monotonic()
RUNNING = True


def _handle_sig(_signum, _frame):
    global RUNNING
    RUNNING = False


def _load_deploy_info() -> dict:
    for path in DEPLOY_INFO_PATHS:
        try:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
    return {}


def main():
    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT, _handle_sig)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(1.0)
    try:
        sock.bind(('0.0.0.0', BEACON_PORT))
    except OSError as exc:
        print(f'[agv_beacon] Aviso: nao foi possivel abrir UDP :{BEACON_PORT}: {exc}', flush=True)
        sys.exit(0)

    print(f'[agv_beacon] Descoberta automatica ativa em UDP 0.0.0.0:{BEACON_PORT}', flush=True)

    while RUNNING:
        try:
            raw, addr = sock.recvfrom(512)
        except socket.timeout:
            continue
        except OSError:
            break

        text = raw.decode('utf-8', errors='ignore').strip()
        if not text.startswith('AGV_DISCOVER'):
            continue

        reply = {
            'robot': 'ELETRON-AGV',
            'hostname': socket.gethostname(),
            'web_port': WEB_PORT,
            'ssh_user': SSH_USER,
            'uptime_s': round(time.monotonic() - START_TIME, 1),
            'deploy_info': _load_deploy_info(),
        }
        try:
            sock.sendto(json.dumps(reply).encode('utf-8'), addr)
        except OSError:
            pass

    sock.close()


if __name__ == '__main__':
    main()
