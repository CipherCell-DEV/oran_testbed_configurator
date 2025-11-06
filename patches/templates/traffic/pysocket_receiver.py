import argparse
import socket


def run_tcp(host: str, port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(1)
        print(f"Listening on {host}:{port} ...")
        conn, addr = srv.accept()
        with conn:
            print(f"Connection from {addr}")
            total = 0
            while True:
                data = conn.recv(65536)
                if not data:
                    break
                total += len(data)
            print(f"Connection closed. Total bytes received: {total}")


def run_udp(host: str, port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as srv:
        srv.bind((host, port))
        print(f"Listening on {host}:{port} ...")
        total = 0
        try:
            while True:
                data, addr = srv.recvfrom(65536)
                total += len(data)
        except KeyboardInterrupt:
            pass
        print(f"Stopped. Total bytes received: {total}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0", help="Listen address (default 0.0.0.0)")
    p.add_argument("--port", type=int, default=5301, help="Port (default 5301)")
    p.add_argument("--udp", action="store_true", help="Use UDP instead of TCP")
    args = p.parse_args()

    if args.udp:
        run_udp(args.host, args.port)
    else:
        run_tcp(args.host, args.port)
