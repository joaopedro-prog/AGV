#!/usr/bin/env python3
"""Proxy TCP leve para expor o Dashboard (:8085) no localhost:8080 do Windows."""

import socket
import sys
import threading

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
TARGET_HOST = sys.argv[2] if len(sys.argv) > 2 else '172.17.0.1'
TARGET_PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 8085


def shutdown_and_close(sock: socket.socket):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


def pipe(src: socket.socket, dst: socket.socket):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        # Envia FIN imediato ao fechar para nao travar HTTP/1.0 sem Content-Length
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle_client(client_sock: socket.socket):
    try:
        remote_sock = socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=5.0)
        remote_sock.settimeout(None)
    except OSError:
        shutdown_and_close(client_sock)
        return

    t1 = threading.Thread(target=pipe, args=(client_sock, remote_sock), daemon=True)
    t2 = threading.Thread(target=pipe, args=(remote_sock, client_sock), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    shutdown_and_close(client_sock)
    shutdown_and_close(remote_sock)


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_HOST, LISTEN_PORT))
    srv.listen(64)
    print(f'[tcp_proxy] {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}', flush=True)
    while True:
        client_sock, _ = srv.accept()
        threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()


if __name__ == '__main__':
    main()
