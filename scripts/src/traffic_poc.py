import subprocess
import argparse
import os
import time
from model.traffic_config import TrafficConfig
import matplotlib.pyplot as plt
import numpy as np

base_cmd = ['docker', 'compose', 'exec']

def run_ping(destination: str, packet_size: int, workdir: str):
    cmd = base_cmd + ['ue1', 'time', 'ip', 'netns', 'exec', 'ue1', 'ping', '-s', str(packet_size), '-c', '1', destination ]
    print(' '.join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=workdir, timeout=1)
    if result.returncode != 0:
        print(result.stderr if result.stderr else "ping failed.")

def precalculate_traffic_array(interval, duration, packet_size, granularity=0.1):
    """
    Precalculate an array of instantaneous traffic (in MB) with the given granularity (in seconds).
    Each entry is the traffic sent at that specific time slot.
    """
    num_slots = int(duration / granularity)
    traffic_array = np.zeros(num_slots, dtype=float)

    for i in range(num_slots):
        t = i * granularity
        if (np.isclose(t % interval, 0, atol=granularity / 2)
                or np.isclose(t % interval, interval, atol=granularity / 2)):
            traffic_array[i] = packet_size / (1024 * 1024)
    return traffic_array

def plot_traffic_pattern(traffic_array, duration, granularity=0.1):
    """
    Plot the traffic pattern over time.
    """
    time_axis = np.arange(0, duration, granularity)[:len(traffic_array)]
    plt.figure(figsize=(12, 4))
    plt.step(time_axis, traffic_array, where='post')
    plt.xlabel('Time (s)')
    plt.ylabel('Instantaneous Traffic (MB)')
    plt.title('Traffic Pattern Over Time')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

def run_periodic_traffic(config_path: str, destination: str, workdir: str):
    config = TrafficConfig.from_yaml(config_path)
    if not config.periodic:
        print("No periodic traffic configuration found in YAML.")
        return
    interval = config.periodic.interval
    duration = config.periodic.duration
    size = config.periodic.size
    granularity = 0.1  # 100 ms
    traffic_array = precalculate_traffic_array(interval, duration, size, granularity)

    plot_traffic_pattern(traffic_array, duration, granularity)

    start_time = time.time()
    next_event = 0.0
    for i in range(len(traffic_array)):
        t = i * granularity
        if t >= next_event:
            run_ping(destination, size, workdir)
            next_event += interval
        next_slot = (i + 1) * granularity
        sleep_time = start_time + next_slot - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute periodic traffic in the Docker Compose container.')
    parser.add_argument('--gnb-address', type=str, default='10.45.1.1', help='Destination IP address')
    parser.add_argument('--ue-address', type=str, default='10.45.1.2', help='Destination IP address')
    parser.add_argument('--packet-size', type=int, default=10008, help='Packet size in bytes (overridden by YAML)')
    parser.add_argument('--workdir', type=str, default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')), help='Working directory for the container')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'traffic.yaml'), help='Path to traffic.yaml config')
    args = parser.parse_args()
    run_periodic_traffic(args.config, args.gnb_address, args.workdir)
