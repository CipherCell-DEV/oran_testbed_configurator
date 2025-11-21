import argparse
import os
import socket
import sys


PAYLOAD = '{RANDOM}'  # Or '{RANDOM}' for random traffic


def gen_payload(size: int):
    return os.urandom(size) if PAYLOAD == '{RANDOM}' else ((PAYLOAD * (size // (len(PAYLOAD)) + 1))[:size]).encode()


def run_tcp(host, port):
    print(f"Connecting to {host}:{port} ...", flush=True)
    with (socket.create_connection((host, port)) as sock):
        print("Connected. Waiting for commands (packet sizes)...", flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "stop"):
                print("Exiting on command.", flush=True)
                break
            try:
                size = int(line)
                if size <= 0:
                    print("Packet size must be positive, skipping.")
                    continue
            except ValueError:
                print(f"Ignoring invalid input: {line}")
                continue

            try:
                sock.sendall(gen_payload(size))
            except BrokenPipeError:
                print("Connection closed by server.", flush=True)
                break
            except Exception as e:
                print(f"Send error: {e}", flush=True)
                break


def run_udp(host, port):
    print(f"Target {host}:{port}. Waiting for commands (packet sizes)...", flush=True)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "stop"):
                print("Exiting on command.", flush=True)
                break
            try:
                size = int(line)
                if size <= 0:
                    print("Packet size must be positive, skipping.")
                    continue
                if size > 65500:
                    print('Packet size must be < 65.5 kB when using UDP. Sending 65.5 kB now.')
                    size = 65500
            except ValueError:
                print(f"Ignoring invalid input: {line}")
                continue

            sock.sendto(gen_payload(size), (host, port))
            print(f"Sent {size} bytes.", flush=True)


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
