import argparse
import os
import socket
import sys


def run_tcp(host, port):
    print(f"[TCP] Connecting to {host}:{port} ...", flush=True)
    with socket.create_connection((host, port)) as sock:
        print("[TCP] Connected. Waiting for commands (packet sizes)...", flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "stop"):
                print("[TCP] Exiting on command.", flush=True)
                break
            try:
                size = int(line)
                if size <= 0:
                    print("Packet size must be positive.")
                    continue
            except ValueError:
                print(f"Ignoring invalid input: {line}")
                continue

            payload = os.urandom(size)
            try:
                sock.sendall(payload)
                print(f"[TCP] Sent {size} bytes.", flush=True)
            except BrokenPipeError:
                print("[TCP] Connection closed by server.", flush=True)
                break
            except Exception as e:
                print(f"[TCP] Send error: {e}", flush=True)
                break


def run_udp(host, port):
    print(f"[UDP] Target {host}:{port}. Waiting for commands (packet sizes)...", flush=True)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "stop"):
                print("[UDP] Exiting on command.", flush=True)
                break
            try:
                size = int(line)
                if size <= 0:
                    print("Packet size must be positive.")
                    continue
                if size > 65500:
                    print('Packet size must be < 65.5 kB when using UDP. Sending 65.5 kB now')
                    size = 65500
            except ValueError:
                print(f"Ignoring invalid input: {line}")
                continue

            payload = os.urandom(size)
            sock.sendto(payload, (host, port))
            print(f"[UDP] Sent {size} bytes.", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Interactive TCP/UDP client")
    p.add_argument("host", help="Target host or IP")
    p.add_argument("--port", type=int, default=5301, help="Port (default 5301)")
    p.add_argument("--udp", action="store_true", help="Use UDP instead of TCP")
    args = p.parse_args()

    if args.udp:
        run_udp(args.host, args.port)
    else:
        run_tcp(args.host, args.port)
