from functools import singledispatchmethod
from random import randint
from typing import Any

import numpy as np
from matplotlib import pyplot as plt
from numpy import dtype, ndarray

from model.traffic_config import Pause, TrafficParameters, OverlapTrafficConfig, TrafficSequenceConfig, \
    DistributedTrafficConfig, RandomTrafficConfig, PeriodicTrafficConfig, DistributionType


class TrafficPlanGenerator:

    def __init__(self, parameters: TrafficParameters):
        self.__traffic = np.zeros(0, dtype=int)
        self.__granularity = parameters.granularity

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
        new_traffic = np.pad(overlapped_traffic, (offset_slots, new_size - offset_slots - overlapped_traffic.size))
        self.__traffic = old_traffic + new_traffic

    @singledispatchmethod
    def __generate_traffic(self, config) -> ndarray[
        tuple[int], dtype[Any]]:  # noqa: ARG001 pylint: disable=unused-argument
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
                generated_traffic[idx] += randint(config.min_size, config.max_size)
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
            mean = num_slots / 2 if config.mean is None else config.mean * num_slots
            std = num_slots / 6 if config.variance is None else np.sqrt(config.variance)
            slot_indices = np.arange(num_slots)
            weights = np.exp(-0.5 * ((slot_indices - mean) / std) ** 2)
            weights /= (std * np.sqrt(2 * np.pi))
            normalized_weights = weights / np.sum(weights)
            generated_traffic = (normalized_weights * config.cumulative_size).astype(int)
        elif config.distribution == DistributionType.uniform:
            weights = np.ones(num_slots)
            normalized_weights = weights / np.sum(weights)
            generated_traffic = (normalized_weights * config.cumulative_size).astype(int)
        elif config.distribution == DistributionType.exponential:
            slot_indices = np.arange(num_slots)
            lambda_ = 3.0 / num_slots if config.lambda_ is None else config.lambda_
            multiplier = num_slots - 1 - slot_indices if config.reverse else slot_indices
            weights = np.exp(-lambda_ * multiplier)
            normalized_weights = weights / np.sum(weights)
            generated_traffic = (normalized_weights * config.cumulative_size).astype(int)
        else:
            print('Unknown distribution type')
            return np.zeros(0, dtype=int)

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
    def _(self, config: TrafficSequenceConfig) -> ndarray[tuple[int], dtype[Any]]:
        params = TrafficParameters(100, '', '', '', False)
        tpg = TrafficPlanGenerator(params)
        for tconfig in config.sequence:
            tpg.__append_traffic(tpg.__generate_traffic(tconfig))
        return tpg.traffic

    @__generate_traffic.register
    def _(self, config: OverlapTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        params = TrafficParameters(100, '', '', '', False)
        tpg = TrafficPlanGenerator(params)
        for (offset, tconfig) in config.overlaps:
            tpg.__overlap_traffic(tpg.__generate_traffic(tconfig), offset)
        return tpg.traffic

    @__generate_traffic.register
    def _(self, config: Pause) -> ndarray[tuple[int], dtype[Any]]:
        return np.zeros(int(config.duration / self.__granularity), dtype=int)

    def plot(self, traffic: ndarray[tuple[int], dtype[Any]] = None):
        if traffic is None:
            traffic = self.__traffic
        time_axis = np.arange(0, traffic.size * self.__granularity, self.__granularity)[:len(traffic)]
        plt.figure(figsize=(12, 4))
        plt.step(time_axis, list(map(lambda x: x / 1000, traffic)), where='post')
        plt.xlabel('Time (ms)')
        plt.ylabel('Instantaneous Traffic (in kB)')
        plt.title('Traffic Over Time')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
