"""
Traffic plan generator for time-based traffic scheduling.

Converts high-level traffic configurations into time-slotted traffic arrays
that define how much traffic is sent at which time from / to which UE.
"""

from functools import singledispatchmethod
from random import randint
from typing import Any

import numpy as np
from matplotlib import pyplot as plt
from numpy import dtype, ndarray

from trafficker.model.traffic_config import *
from trafficker.model.traffic_parameters import TrafficParameters


class TrafficPlanGenerator:
    """
    Generates time-slotted traffic plans from configuration.

    Traffic is discretized into time slots based on the granularity parameter.
    Each slot contains the number of bytes to send during that time interval from / to a specific UE.
    """

    def __init__(self, parameters: TrafficParameters):
        """
        Initialize traffic plan generator.

        Args:
            parameters: Global traffic parameters including granularity
        """
        self.__traffic = {}
        self.__granularity = parameters.granularity
        self.__parameters = parameters

    def from_plan(self, sequence_config: dict):
        """
        Generate traffic from configuration dict.

        Args:
            sequence_config: Dictionary mapping UE IDs to TrafficSequenceConfig
        """
        for ue_id, traffic in sequence_config.items():
            for config in traffic.sequence:
                self.__append_traffic(ue_id, self.__generate_traffic(config))

    @property
    def traffic(self):
        """Get copy of generated traffic dictionary."""
        return self.__traffic.copy()

    def __append_traffic(self, ue_id: str, appended_traffic: ndarray[tuple[int], dtype[Any]]):
        """Append traffic to end of existing traffic for a UE."""
        if ue_id not in self.__traffic:
            self.__traffic[ue_id] = np.zeros(0, dtype=int)
        self.__traffic[ue_id] = np.append(self.__traffic[ue_id], appended_traffic)

    def __overlap_traffic(self, ue_id: str, overlapped_traffic: ndarray[tuple[int], dtype[Any]], offset_ms: int):
        """Add overlapping traffic at specified time offset."""
        if ue_id not in self.__traffic:
            self.__traffic[ue_id] = np.zeros(0, dtype=int)
        offset_slots = int(offset_ms / self.__granularity)
        new_size = max(self.__traffic[ue_id].size, offset_slots + overlapped_traffic.size)
        old_traffic = np.pad(self.__traffic[ue_id], (0, new_size - self.__traffic[ue_id].size), mode='constant')
        new_traffic = np.pad(overlapped_traffic, (offset_slots, new_size - offset_slots - overlapped_traffic.size))
        self.__traffic[ue_id] = old_traffic + new_traffic

    @singledispatchmethod
    def __generate_traffic(self, config) -> ndarray[tuple[int], dtype[Any]]:
        """Default handler for unknown traffic config types."""
        print('Unknown traffic config ', config)
        return np.zeros(0, dtype=int)

    @__generate_traffic.register
    def _(self, config: PeriodicTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        """Generate periodic traffic with fixed interval and packet size."""
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
        """Generate random traffic with uniformly distributed packet sizes."""
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
        Generate traffic distributed over time according to statistical distribution.

        The cumulative_size bytes are distributed across time slots according to
        the specified distribution (normal, uniform, or exponential). The sum of
        all bytes equals cumulative_size.

        Args:
            config: Distribution configuration with type and parameters

        Returns:
            Array of bytes per time slot
        """
        num_slots = int(config.duration / self.__granularity)
        generated_traffic = np.zeros(num_slots, dtype=int)

        if num_slots == 0:
            return generated_traffic

        # Generate probability distribution weights
        if config.distribution == DistributionType.NORMAL:
            mean = num_slots / 2 if config.mean is None else config.mean * num_slots
            std = num_slots / 6 if config.variance is None else np.sqrt(config.variance)
            slot_indices = np.arange(num_slots)
            weights = np.exp(-0.5 * ((slot_indices - mean) / std) ** 2)
            weights /= (std * np.sqrt(2 * np.pi))
        elif config.distribution == DistributionType.UNIFORM:
            weights = np.ones(num_slots)
        elif config.distribution == DistributionType.EXPONENTIAL:
            slot_indices = np.arange(num_slots)
            lambda_ = 3.0 / num_slots if config.lambda_ is None else config.lambda_
            multiplier = num_slots - 1 - slot_indices if config.reverse else slot_indices
            weights = np.exp(-lambda_ * multiplier)
        else:
            print('Unknown distribution type')
            return np.zeros(0, dtype=int)

        # Normalize and distribute cumulative_size across slots
        normalized_weights = weights / np.sum(weights)
        generated_traffic = (normalized_weights * config.cumulative_size).astype(int)

        # Handle rounding errors to ensure exact cumulative_size
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
        """Generate sequential traffic by concatenating sub-configurations."""
        tpg = TrafficPlanGenerator(self.__parameters)
        for tconfig in config.sequence:
            tpg.__append_traffic('dummy', tpg.__generate_traffic(tconfig))
        return tpg.traffic['dummy']

    @__generate_traffic.register
    def _(self, config: OverlapTrafficConfig) -> ndarray[tuple[int], dtype[Any]]:
        """Generate overlapping traffic by adding sub-configurations at time offsets."""
        tpg = TrafficPlanGenerator(self.__parameters)
        for (offset, tconfig) in config.overlaps:
            tpg.__overlap_traffic('dummy', tpg.__generate_traffic(tconfig), offset)
        return tpg.traffic['dummy']

    @__generate_traffic.register
    def _(self, config: Pause) -> ndarray[tuple[int], dtype[Any]]:
        """Generate pause (zero traffic) for specified duration."""
        return np.zeros(int(config.duration / self.__granularity), dtype=int)

    def plot(self,
             traffic: dict = None,
             plot_single: bool = True,
             plot_cumulative: bool = True,
             time_unit: str = 's'):
        """
        Plot generated traffic plan.

        Args:
            traffic: Traffic dict to plot (defaults to self.traffic)
            plot_single: Whether to plot individual UE traffic (defaults to True)
            plot_cumulative: Whether to plot cumulative traffic across all UEs (defaults to True)
            time_unit: Time unit for x-axis ('ms', 's', 'm', 'h') (defaults to s)
        """

        def plot_traffic(name, p_trfc):
            """Helper to plot single traffic array."""
            match time_unit:
                case 's':
                    time_dividend = 1000
                case 'm':
                    time_dividend = 1000 * 60
                case 'h':
                    time_dividend = 1000 * 60 * 60
                case _:
                    time_dividend = 1
            time_axis_ms = np.arange(0, p_trfc.size * self.__granularity, self.__granularity)[:len(p_trfc)]
            plt.step(time_axis_ms / time_dividend, list(map(lambda x: x / 1000, p_trfc)), label=name)

        if traffic is None:
            traffic = self.__traffic

        cumulative_tpg = TrafficPlanGenerator(self.__parameters)
        for trfc in traffic.values():
            cumulative_tpg.__overlap_traffic('dummy', trfc, 0)
        cumulative = cumulative_tpg.traffic['dummy']

        plt.figure(figsize=(12, 4))
        if plot_cumulative:
            plot_traffic('Cumulative', cumulative)
        if plot_single:
            for ue_id, traffic_list in traffic.items():
                plot_traffic(ue_id, traffic_list)
        plt.xlabel(f'Time ({time_unit})')
        plt.ylabel('Instantaneous Traffic (in kB)')
        plt.title('Traffic Over Time')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.legend()
        plt.show()
