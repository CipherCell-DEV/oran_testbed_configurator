import subprocess
import argparse
import os
import time
from model.traffic_config import TrafficConfig

base_cmd = ['docker', 'compose', 'exec']

def run_ping(destination: str, packet_size: int, workdir: str):
    cmd = base_cmd + ['ue1', 'ip', 'netns', 'exec', 'ue1', 'ping', '-s', str(packet_size), '-c', '1', destination ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir)
    if result.returncode != 0:
        print(result.stderr if result.stderr else "Command failed.")

def run_periodic_traffic(config_path: str, destination: str, workdir: str):
    config = TrafficConfig.from_yaml(config_path)
    if not config.periodic:
        print("No periodic traffic configuration found in YAML.")
        return
    interval = config.periodic.interval
    duration = config.periodic.duration
    size = config.periodic.size
    start_time = time.time()
    while (time.time() - start_time) < duration:
        run_ping(destination, size, workdir)
        time.sleep(interval)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute periodic traffic in the Docker Compose container.')
    parser.add_argument('--gnb-address', type=str, default='10.45.1.1', help='Destination IP address')
    parser.add_argument('--ue-address', type=str, default='10.45.1.2', help='Destination IP address')
    parser.add_argument('--packet-size', type=int, default=10008, help='Packet size in bytes (overridden by YAML)')
    parser.add_argument('--workdir', type=str, default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')), help='Working directory for the container')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'traffic.yaml'), help='Path to traffic.yaml config')
    args = parser.parse_args()
    run_periodic_traffic(args.config, args.gnb_address, args.workdir)
