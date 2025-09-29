import argparse
import os
import time
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from numpy import ndarray, dtype

from UEContainer import UEContainer
from model.traffic_config import PeriodicTrafficConfig, BaseTrafficConfig


class TrafficPlanGenerator:

    def __init__(self):
        self.__traffic = np.zeros(0, dtype=int)
        self.__granularity = 100  # TODO: Get from config

    def append_traffic(self, traffic: ndarray[tuple[int], dtype[Any]]):
        self.__traffic = np.append(self.__traffic, traffic)
    
    def overlap_traffic(self, traffic: ndarray[tuple[int], dtype[Any]], offset: int):
        pass

    @staticmethod
    def generate_periodic_traffic(config: PeriodicTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        num_slots = int(config.duration / config.granularity)
        generated_traffic = np.zeros(num_slots, dtype=int)

        current_time = 0.0
        while current_time < config.duration:
            idx = int(current_time / config.granularity)
            if idx < num_slots:
                generated_traffic[idx] += config.packet_size
            current_time += config.interval

        return generated_traffic

    def get_traffic_plan(self):
        return self.__traffic


class TrafficExecutor:

    def __init__(self, traffic_plan: ndarray[tuple[int], dtype[Any]]):
        self.traffic_plan: ndarray[tuple[int], dtype[Any]] = traffic_plan

    def execute(self, config: BaseTrafficConfig):
        ue_container = UEContainer(config.workdir)
        ue_container.start_session()

        try:
            for instant_traffic in self.traffic_plan:
                start_time = time.time()
                if (instant_traffic > 0
                        and not ue_container.run_ping(config.gnb_address, instant_traffic, config.granularity)):
                    print('Ping did not run successfully')
                rest_duration = (start_time + (config.granularity / 1000)) - time.time()
                if rest_duration > 0:
                    time.sleep(rest_duration)
        finally:
            ue_container.close_session()


def plot_traffic_pattern(traffic_array, granularity=100):
    """
    Plot the traffic pattern over time.
    """
    time_axis = np.arange(0, traffic_array.size * granularity, granularity)[:len(traffic_array)]
    plt.figure(figsize=(12, 4))
    plt.step(time_axis, traffic_array, where='post')
    plt.xlabel('Time (ms)')
    plt.ylabel('Instantaneous Traffic (in B)')
    plt.title('Traffic Pattern Over Time')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute periodic traffic in the Docker Compose container.')
    parser.add_argument('--gnb-address', type=str, default='10.45.1.1', help='Destination IP address')
    parser.add_argument('--ue-address', type=str, default='10.45.1.2', help='Destination IP address')
    parser.add_argument('--workdir', type=str,
                        default=os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')),
                        help='Working directory for the container')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'traffic.yaml'),
                        help='Path to traffic.yaml config')
    args = parser.parse_args()

    base_config = BaseTrafficConfig.from_yaml(args.config)
    generator = TrafficPlanGenerator()
    generator.append_traffic(generator.generate_periodic_traffic(PeriodicTrafficConfig.from_yaml(args.config)))
    traffic = generator.get_traffic_plan()

    plot_traffic_pattern(traffic)

    #executor = TrafficExecutor(traffic)
    #executor.execute(base_config)
