from functools import singledispatchmethod
from random import randint
from typing import Any

import numpy as np
from matplotlib import pyplot as plt
from numpy import dtype, ndarray

from model.traffic.traffic_config import Pause, TrafficParameters, OverlapTrafficConfig, TrafficSequenceConfig, \
    DistributedTrafficConfig, RandomTrafficConfig, PeriodicTrafficConfig, DistributionType, Direction


class TrafficPlanGenerator:

    def __init__(self, parameters: TrafficParameters):
        self.__traffic = {}
        self.__granularity = parameters.granularity

    def from_plan(self, sequence_config: dict):
        for ue_id, traffic in sequence_config.items():
            for config in traffic.sequence:
                self.__append_traffic(ue_id, self.__generate_traffic(config))

    @property
    def traffic(self):
        return self.__traffic.copy()

    def __append_traffic(self, ue_id: str, appended_traffic: ndarray[tuple[int], dtype[Any]]):
        if ue_id not in self.__traffic:
            self.__traffic[ue_id] = np.zeros(0, dtype=int)
        self.__traffic[ue_id] = np.append(self.__traffic[ue_id], appended_traffic)

    def __overlap_traffic(self, ue_id: str, overlapped_traffic: ndarray[tuple[int], dtype[Any]], offset_ms: int):
        if ue_id not in self.__traffic:
            self.__traffic[ue_id] = np.zeros(0, dtype=int)
        offset_slots = int(offset_ms / self.__granularity)
        new_size = max(self.__traffic[ue_id].size, offset_slots + overlapped_traffic.size)
        old_traffic = np.pad(self.__traffic[ue_id], (0, new_size - self.__traffic[ue_id].size), mode='constant')
        new_traffic = np.pad(overlapped_traffic, (offset_slots, new_size - offset_slots - overlapped_traffic.size))
        self.__traffic[ue_id] = old_traffic + new_traffic

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
        tpg = TrafficPlanGenerator(TrafficParameters(100, '', '', '', '', Direction.coreToUE, '', False))
        for tconfig in config.sequence:
            tpg.__append_traffic('dummy', tpg.__generate_traffic(tconfig))
        return tpg.traffic['dummy']

    @__generate_traffic.register
    def _(self, config: OverlapTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        tpg = TrafficPlanGenerator(TrafficParameters(100, '', '', '', '', Direction.coreToUE, '', False))
        for (offset, tconfig) in config.overlaps:
            tpg.__overlap_traffic('dummy', tpg.__generate_traffic(tconfig), offset)
        return tpg.traffic['dummy']

    @__generate_traffic.register
    def _(self, config: Pause) -> ndarray[tuple[int], dtype[Any]]:
        return np.zeros(int(config.duration / self.__granularity), dtype=int)

    def plot(self, traffic: dict = None, plot_single: bool = True):
        def plot_traffic(name, trfc):
            time_axis = np.arange(0, trfc.size * self.__granularity, self.__granularity)[:len(trfc)]
            plt.step(time_axis, list(map(lambda x: x / 1000, trfc)), label=name)

        if traffic is None:
            traffic = self.__traffic

        cumulative_tpg = TrafficPlanGenerator(TrafficParameters(100, '', '', '', '', Direction.coreToUE, '', False))
        for trfc in traffic.values():
            cumulative_tpg.__overlap_traffic('dummy', trfc, 0)
        cumulative = cumulative_tpg.traffic['dummy']

        plt.figure(figsize=(12, 4))
        plot_traffic('Cumulative', cumulative)
        if plot_single:
            for ue_id, traffic_list in traffic.items():
                plot_traffic(ue_id, traffic_list)
        plt.xlabel('Time (ms)')
        plt.ylabel('Instantaneous Traffic (in kB)')
        plt.title('Traffic Over Time')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.legend()
        plt.show()
