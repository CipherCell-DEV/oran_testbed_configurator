"""
Traffic configuration models and parsing utilities.

This module defines data structures for traffic generation configurations
in the O-RAN testbed, including traffic parameters, patterns, and distribution types.
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import yaml


def parse_time(time_str: str) -> int:
    """
    Parse a time string into milliseconds.

    Args:
        time_str: Time string with optional decimal value and unit
                  (e.g., '10ms', '2s', '1.5m', '1h')

    Returns:
        Time in milliseconds as integer

    Raises:
        ValueError: If format is invalid or unit is not recognized
    """
    match = re.match(r"(\d+(?:\.\d+)?) *(ms|s|m|h)", time_str.strip())
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
    value, unit = match.groups()
    value = float(value)
    match unit:
        case 'ms':
            return int(value)
        case 's':
            return int(value * 1000)
        case 'm':
            return int(value * 60 * 1000)
        case 'h':
            return int(value * 3600 * 1000)
        case _:
            raise ValueError(f"Unknown time unit: {unit}")


def parse_bytes(byte_str: str) -> int:
    """
    Parse a byte size string into bytes.

    Args:
        byte_str: Size string with value and unit (e.g., '10B', '2kB', '1.5MB', '1GB')

    Returns:
        Size in bytes as integer

    Raises:
        ValueError: If format is invalid or unit is not recognized
    """
    match = re.match(r"(-?\d+(?:\.\d+)?) *(B|kB|MB|GB)", byte_str.strip())
    if not match:
        raise ValueError(f"Invalid size format: {byte_str}")
    value, unit = match.groups()
    value = float(value)
    match unit:
        case 'B':
            return int(value)
        case 'kB':
            return int(value * 1_000)
        case 'MB':
            return int(value * 1_000_000)
        case 'GB':
            return int(value * 1_000_000_000)
        case _:
            raise ValueError(f"Unknown unit: {unit}")


class Direction(Enum):
    """Traffic direction between UE and Core."""

    UE_TO_CORE = 'UL'  # Uplink: UE to Core
    CORE_TO_UE = 'DL'  # Downlink: Core to UE
    BIDIRECTIONAL = 'BI'


@dataclass
class TrafficParameters:
    """
    Global parameters for traffic generation.

    Attributes:
        granularity: Time resolution in milliseconds for traffic scheduling
        core_service: Docker service name of the 5G core
        core_address: IP address of the 5G core
        user_equipments: Dictionary mapping UE IDs to connection info
        direction: Traffic direction (UL/DL/BI)
        workdir: Working directory containing main docker-compose.yaml
        loop: Whether to repeat traffic generation infinitely
        use_nist: Whether to use NIST testbed instead of our own
        nist_vm: SSH connection string for NIST VM (or 'local'), not necessary when use_nist is false
        use_udp: Whether to use UDP instead of TCP
    """

    granularity: int
    core_service: str
    core_address: str
    user_equipments: dict
    direction: Direction
    workdir: str
    loop: bool
    use_nist: bool
    nist_vm: str
    use_udp: bool

    @classmethod
    def load_yaml(cls, path: str) -> Optional['TrafficParameters']:
        """
        Load traffic parameters from a YAML configuration file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            TrafficParameters instance if 'parameters' section exists, None otherwise
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'parameters' in data:
            return TrafficParameters(
                granularity=parse_time(data['parameters'].get('granularity', '100ms')),
                core_service=data['parameters']['core'].get('service', '5gc'),
                core_address=data['parameters']['core'].get('address', '10.45.1.1'),
                user_equipments=data['parameters'].get('user-equipments', {}),
                direction=Direction(data['parameters'].get('direction', 'core->ue')),
                workdir=os.path.abspath(
                    os.path.join(os.path.dirname(path), data['parameters'].get('workdir', '..'))),
                loop=data['parameters'].get('loop', False),
                use_nist=data['parameters'].get('use_nist', False),
                nist_vm=data['parameters'].get('nist_vm_ssh', 'local'),
                use_udp=data['parameters'].get('use_udp', False),
            )
        else:
            return None


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
