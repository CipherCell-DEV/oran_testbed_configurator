import argparse
import os
import subprocess
import time

import matplotlib.pyplot as plt
import numpy as np

from model.traffic_config import TrafficConfig

DEFAULT_GRANULARITY = 0.1  # 100 ms
traffic = 0


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

    def run_ping(self, destination: str, packet_size: int, timeout: float = DEFAULT_GRANULARITY):
        """Run a ping command in the persistent session"""
        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        ping_cmd = f'ip netns exec ue1 ping -s {packet_size} -c 1 {destination}'
        cmd = f'{ping_cmd}; echo "EXIT_CODE:$?"'

        try:
            self.process.stdin.write(cmd + '\n')
            self.process.stdin.flush()
            global traffic
            traffic += packet_size

            start_time = time.time()
            while time.time() - start_time < timeout:
                import select
                ready, _, _ = select.select([self.process.stdout], [], [], timeout)
                if ready and (line := self.process.stdout.readline()):
                    line = line.strip()
                    if line.startswith("EXIT_CODE:"):
                        exit_code = int(line.split(":")[1])
                        return exit_code == 0
                if self.process.poll() is not None:
                    print("Bash session terminated unexpectedly")
                    return False
            print("Ping command timed out")
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


def precalculate_traffic_array(interval, duration, packet_size, granularity=DEFAULT_GRANULARITY):
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


def plot_traffic_pattern(traffic_array, duration, granularity=DEFAULT_GRANULARITY):
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
    granularity = DEFAULT_GRANULARITY
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
    parser.add_argument('--workdir', type=str,
                        default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')),
                        help='Working directory for the container')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'traffic.yaml'),
                        help='Path to traffic.yaml config')
    args = parser.parse_args()
    run_periodic_traffic(args.config, args.gnb_address, args.workdir)
