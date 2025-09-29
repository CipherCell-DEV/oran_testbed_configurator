import argparse
import os
import subprocess
import time

import matplotlib.pyplot as plt
import numpy as np

from model.traffic_config import TrafficConfig

DEFAULT_GRANULARITY = 100  # ms


class UEContainer:
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.process = None

    def start_session(self):
        """Start a persistent bash session in the UE container"""
        cmd = ['docker', 'compose', 'exec', '-T', 'ue1', 'bash']
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.workdir
        )

    def run_ping(self, destination: str, packet_size: int, timeout: int = DEFAULT_GRANULARITY):
        """Run a ping command in the persistent session"""
        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if packet_size > 60000:
            print('Packet size currently cannot be more than 60 kB! Reducing it to 60 kB.')
            packet_size = 60000

        ping_cmd = f'ip netns exec ue1 ping -s {packet_size} -c 1 {destination}'
        cmd = f'{ping_cmd}; echo "EXIT_CODE:$?"'

        try:
            self.process.stdin.write(cmd + '\n')
            self.process.stdin.flush()
            timeout_s = timeout / 1000 - 0.01

            start_time = time.time()
            while time.time() - start_time < timeout_s:
                import select
                ready, _, _ = select.select([self.process.stdout], [], [], timeout_s)
                if ready and (line := self.process.stdout.readline()):
                    line = line.strip()
                    if line.startswith("EXIT_CODE:"):
                        return int(line.split(":")[1]) == 0
                if self.process.poll() is not None:
                    print("Bash session terminated unexpectedly")
                    return False
            print("Ping timed out")
            return False
        except Exception as e:
            print(f"Ping failed: {e}")
            return False

    def close_session(self):
        """Close the persistent session"""
        if self.process:
            try:
                self.process.stdin.write('exit\n')
                self.process.stdin.flush()
                self.process.wait(timeout=2)
            except:
                self.process.terminate()
            finally:
                self.process = None
                print("Closed UE container session")


def precalculate_periodic_traffic_array(interval, duration, packet_size, granularity=DEFAULT_GRANULARITY):
    """
    Precalculate an array of instantaneous traffic (in B) with the given granularity (in seconds).
    Each entry is the traffic sent at that specific time slot.
    """
    num_slots = int(duration / granularity)
    traffic_array = np.zeros(num_slots, dtype=int)

    current_time = 0.0
    while current_time < duration:
        idx = int(current_time / granularity)

        if idx < num_slots:
            traffic_array[idx] += packet_size

        current_time += interval

    return traffic_array


def plot_traffic_pattern(traffic_array, duration, granularity=DEFAULT_GRANULARITY):
    """
    Plot the traffic pattern over time.
    """
    time_axis = np.arange(0, duration, granularity)[:len(traffic_array)]
    plt.figure(figsize=(12, 4))
    plt.step(time_axis, traffic_array, where='post')
    plt.xlabel('Time (s)')
    plt.ylabel('Instantaneous Traffic (in B)')
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
    granularity = DEFAULT_GRANULARITY
    traffic_array = precalculate_periodic_traffic_array(interval, duration, size, granularity)

    plot_traffic_pattern(traffic_array, duration, granularity)

    ue_container = UEContainer(workdir)
    ue_container.start_session()

    try:
        for instant_traffic in traffic_array:
            start_time = time.time()
            if instant_traffic > 0 and not ue_container.run_ping(destination, instant_traffic, granularity):
                print('Ping did not run successfully')
            if (sleep_time := (start_time + (granularity / 1000)) - time.time()) > 0:
                time.sleep(sleep_time)
    finally:
        ue_container.close_session()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute periodic traffic in the Docker Compose container.')
    parser.add_argument('--gnb-address', type=str, default='10.45.1.1', help='Destination IP address')
    parser.add_argument('--ue-address', type=str, default='10.45.1.2', help='Destination IP address')
    parser.add_argument('--packet-size', type=int, default=10008, help='Packet size in bytes (overridden by YAML)')
    parser.add_argument('--workdir', type=str,
                        default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')),
                        help='Working directory for the container')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'traffic.yaml'),
                        help='Path to traffic.yaml config')
    args = parser.parse_args()
    run_periodic_traffic(args.config, args.gnb_address, args.workdir)
