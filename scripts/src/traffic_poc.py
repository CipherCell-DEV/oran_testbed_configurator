import argparse
import os
import random
import time
from functools import singledispatchmethod
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from numpy import ndarray, dtype

from UEContainer import UEContainer
from model.traffic_config import PeriodicTrafficConfig, TrafficParameters, from_yaml, TrafficSequenceConfig, \
    OverlapTrafficConfig, Pause, RandomTrafficConfig, DistributedTrafficConfig, DistributionType


class TrafficPlanGenerator:

    def __init__(self):
        self.__traffic = np.zeros(0, dtype=int)
        self.__granularity = 100  # TODO: Get from config

    def from_plan(self, sequence_config: TrafficSequenceConfig):
        for config in sequence_config.sequence:
            self.__append_traffic(self.__generate_traffic(config))

    @property
    def traffic(self):
        return self.__traffic.copy()

    def __append_traffic(self, appended_traffic: ndarray[tuple[int], dtype[Any]]):
        self.__traffic = np.append(self.__traffic, appended_traffic)

    def __overlap_traffic(self, overlapped_traffic: ndarray[tuple[int], dtype[Any]], offset_ms: int):
        offset_slots = int(offset_ms / self.__granularity)
        new_size = max(self.__traffic.size, offset_slots + overlapped_traffic.size)
        old_traffic = np.pad(self.__traffic, (0, new_size - self.__traffic.size), mode='constant')
        new_traffic = np.pad(overlapped_traffic,(offset_slots, new_size - offset_slots - overlapped_traffic.size))
        self.__traffic = old_traffic + new_traffic

    @singledispatchmethod
    def __generate_traffic(self, config) -> ndarray[tuple[int], dtype[Any]]:
        print('Unknown traffic config')
        return np.zeros(0, dtype=int)

    @__generate_traffic.register
    def _(self, config: PeriodicTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        num_slots = int(config.duration / self.__granularity)
        generated_traffic = np.zeros(num_slots, dtype=int)

        current_time = 0.0
        while current_time < config.duration:
            idx = int(current_time / self.__granularity)
            if idx < num_slots:
                generated_traffic[idx] += config.packet_size
            current_time += config.interval

        return generated_traffic

    @__generate_traffic.register
    def _(self, config: RandomTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        num_slots = int(config.duration / self.__granularity)
        generated_traffic = np.zeros(num_slots, dtype=int)

        current_time = 0.0
        while current_time < config.duration:
            idx = int(current_time / self.__granularity)
            if idx < num_slots:
                generated_traffic[idx] += random.randint(config.min_size, config.max_size)
            current_time += self.__granularity

        return generated_traffic

    @__generate_traffic.register
    def _(self, config: DistributedTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        """
        Generates a traffic pattern that is distributed according to the type (e.g. normal distribution). The sum of the
        individual bytes is equal to the cumulative size specified.
        :param config: The DistributedTrafficConfig containing the configuration parameters for the distribution.
        :return: A numpy array containing the traffic over time, distributed according to the specified distribution.
        """
        num_slots = int(config.duration / self.__granularity)
        generated_traffic = np.zeros(num_slots, dtype=int)

        if num_slots == 0:
            return generated_traffic

        if config.distribution == DistributionType.normal:
            mean = num_slots / 2
            std = num_slots / 6
            slot_indices = np.arange(num_slots)
            weights = np.exp(-0.5 * ((slot_indices - mean) / std) ** 2)
            weights /= (std * np.sqrt(2 * np.pi))
            normalized_weights = weights / np.sum(weights)
            traffic_values = normalized_weights * config.cumulative_size
            generated_traffic = traffic_values.astype(int)
        elif config.distribution == DistributionType.uniform:
            weights = np.ones(num_slots)
            normalized_weights = weights / np.sum(weights)
            traffic_values = normalized_weights * config.cumulative_size
            generated_traffic = traffic_values.astype(int)
        elif config.distribution == DistributionType.exponential:
            slot_indices = np.arange(num_slots)
            scale = num_slots / 3
            weights = np.exp(-slot_indices / scale)
            normalized_weights = weights / np.sum(weights)
            traffic_values = normalized_weights * config.cumulative_size
            generated_traffic = traffic_values.astype(int)
        else:
            weights = np.ones(num_slots)
            normalized_weights = weights / np.sum(weights)
            traffic_values = normalized_weights * config.cumulative_size
            generated_traffic = traffic_values.astype(int)

        remainder = config.cumulative_size - np.sum(generated_traffic)
        if remainder > 0:
            random_indices = np.random.choice(num_slots, size=min(remainder, num_slots), replace=False)
            generated_traffic[random_indices] += 1
        elif remainder < 0:
            excess = -remainder
            non_zero_indices = np.where(generated_traffic > 0)[0]
            if len(non_zero_indices) > 0:
                for _ in range(min(excess, len(non_zero_indices))):
                    idx = np.random.choice(non_zero_indices)
                    if generated_traffic[idx] > 0:
                        generated_traffic[idx] -= 1

        return generated_traffic

    @__generate_traffic.register
    def _(self, config: OverlapTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        tpg = TrafficPlanGenerator()
        for (offset, tconfig) in config.overlaps:
            tpg.__overlap_traffic(tpg.__generate_traffic(tconfig), offset)
        return tpg.traffic

    @__generate_traffic.register
    def _(self, config: Pause) -> ndarray[tuple[int], dtype[Any]]:
        return np.zeros(int(config.duration / self.__granularity), dtype=int)


class TrafficExecutor:

    def __init__(self, traffic_plan: ndarray[tuple[int], dtype[Any]]):
        self.traffic_plan: ndarray[tuple[int], dtype[Any]] = traffic_plan

    def execute(self, config: TrafficParameters):
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
    plt.title('Traffic Over Time')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute periodic traffic in the Docker Compose container.')
    parser.add_argument('--config', type=str, default=os.path.join(os.path.dirname(__file__), 'traffic.yaml'),
                        help='Path to traffic.yaml config')
    args = parser.parse_args()

    traffic_config = from_yaml(args.config)

    generator = TrafficPlanGenerator()
    generator.from_plan(traffic_config)

    traffic = generator.traffic

    plot_traffic_pattern(traffic)

    # parameters = TrafficParameters.from_yaml(args.config)
    # executor = TrafficExecutor(traffic)
    # executor.execute(parameters)
