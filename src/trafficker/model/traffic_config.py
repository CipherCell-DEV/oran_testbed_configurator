"""
Traffic configuration models and parsing utilities.

This module defines data structures for traffic generation configurations
in the O-RAN testbed, including traffic parameters, patterns, and distribution types.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from trafficker.model.utils import parse_time, parse_bytes


@dataclass
class BaseTrafficConfig:
    """Base configuration for all traffic patterns except sequence and overlap.

    Attributes:
        duration: Total duration of the traffic pattern in milliseconds
    """

    duration: int  # milliseconds


@dataclass
class TrafficSequenceConfig:
    """Sequential traffic configuration combining multiple patterns after each other.

    Attributes:
    sequence: List of traffic configurations to execute in sequence
    """

    sequence: list[BaseTrafficConfig]


@dataclass
class OverlapTrafficConfig:
    """Overlapping traffic patterns with time offsets.

    Attributes:
          overlaps: List of tuples containing (offset_ms, traffic_config) where offset_ms is the time in milliseconds
          to wait before starting the traffic_config, and traffic_config is an instance of a traffic configuration
    """

    overlaps: list[tuple[int, BaseTrafficConfig]]  # (offset_ms, config)


@dataclass
class PeriodicTrafficConfig(BaseTrafficConfig):
    """
    Periodic traffic with fixed packet size and interval.

    Attributes:
        packet_size: Size of each packet in bytes
        interval: Time between packets in milliseconds
    """

    packet_size: int
    interval: int

    @classmethod
    def from_dict(cls, source: dict):
        """
        Create configuration from dictionary.

        Args:
            source: Dictionary with 'duration', 'size', and 'interval' keys

        Returns:
            PeriodicTrafficConfig instance
        """
        return PeriodicTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            packet_size=parse_bytes(source.get('size', '1kB')),
            interval=parse_time(source.get('interval', '100ms'))
        )


@dataclass
class RandomTrafficConfig(BaseTrafficConfig):
    """
    Random traffic with variable packet sizes.

    Attributes:
        duration: Total duration in milliseconds
        min_size: Minimum packet size in bytes
        max_size: Maximum packet size in bytes
    """

    min_size: int
    max_size: int

    @classmethod
    def from_dict(cls, source: dict):
        """
        Create configuration from dictionary.

        Args:
            source: Dictionary with 'duration', 'min_size', and 'max_size' keys

        Returns:
            RandomTrafficConfig instance
        """
        return RandomTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            min_size=parse_bytes(source.get('min_size', '1kB')),
            max_size=parse_bytes(source.get('max_size', '1kB'))
        )


class DistributionType(Enum):
    """Statistical distribution types for traffic generation."""

    NORMAL = 'normal-distribution'
    UNIFORM = 'uniform-distribution'
    EXPONENTIAL = 'exponential-distribution'


@dataclass
class DistributedTrafficConfig(BaseTrafficConfig):
    """
    Traffic distributed over time according to statistical distribution.

    The total cumulative_size bytes are distributed across the duration
    according to the specified distribution type.

    Attributes:
        duration: Total duration in milliseconds
        cumulative_size: Total bytes to send across all time slots
        distribution: Type of statistical distribution
        mean: Mean value for normal distribution (fraction of duration, 0-1)
        variance: Variance for normal distribution
        lambda_: Rate parameter for exponential distribution
        reverse: Reverse exponential distribution direction
    """

    cumulative_size: int
    distribution: DistributionType
    mean: Optional[float] = None
    variance: Optional[float] = None
    lambda_: Optional[float] = None
    reverse: Optional[bool] = None

    @classmethod
    def from_dict(cls, source: dict):
        """
        Create configuration from dictionary.

        Args:
            source: Dictionary with distribution parameters

        Returns:
            DistributedTrafficConfig instance
        """
        return DistributedTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            cumulative_size=parse_bytes(source.get('cumulative_size', '1kB')),
            distribution=DistributionType(source.get('type', 'normal-distribution')),
            mean=source.get('mean'),
            variance=source.get('variance'),
            lambda_=source.get('lambda'),
            reverse=source.get('reverse')
        )


@dataclass
class Pause(BaseTrafficConfig):
    """Traffic pause with no data transmission."""

    @classmethod
    def from_duration(cls, duration):
        """
        Create pause from duration string.

        Args:
            duration: Duration string (e.g., '100ms', '2s')

        Returns:
            Pause instance
        """
        return Pause(duration=parse_time(duration))
