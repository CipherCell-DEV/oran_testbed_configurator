import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import yaml


def parse_time(timestr: str) -> int:
    """Parse a time string like '10s', '2m', '1h', '1.5m', '10ms' into milliseconds (int)."""
    match = re.match(r"(\d+(?:\.\d+)?) *(ms|s|m|h)", timestr.strip())
    if not match:
        raise ValueError(f"Invalid time format: {timestr}")
    value, unit = match.groups()
    value = int(value)
    match unit:
        case 'ms':
            return value
        case 's':
            return value * 1000
        case 'm':
            return value * 60 * 1000
        case 'h':
            return value * 3600 * 1000
        case _:
            raise ValueError(f"Unknown time unit: {unit}")


def _parse_bytes(bytestr: str) -> int:
    """Parse a byte size string like '10B', '2kB', '1MB', '1.5GB' into Bytes (int)."""
    match = re.match(r"(-?\d+(?:\.\d+)?) *(B|kB|MB|GB)", bytestr.strip())
    if not match:
        raise ValueError(f"Invalid size format: {bytestr}")
    value, unit = match.groups()
    value = int(value)
    match unit:
        case 'B':
            return value
        case 'kB':
            return value * 1_000
        case 'MB':
            return value * 1_000_000
        case 'GB':
            return value * 1_000_000_000
        case _:
            raise ValueError(f"Unknown unit: {unit}")


@dataclass
class TrafficParameters:
    granularity: int  # ms
    gnb_address: str  # IP Address
    ue_address: str  # IP Address
    workdir: str  # Path to main docker-compose.yaml
    loop: bool  # Loop traffic infinitely

    @classmethod
    def load_yaml(cls, path: str) -> Optional['TrafficParameters']:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'parameters' in data:
            return TrafficParameters(
                granularity=parse_time(data['parameters'].get('granularity', '100ms')),
                gnb_address=data['parameters'].get('gnb-address', '10.45.1.1'),
                ue_address=data['parameters'].get('ue-address', '10.45.1.2'),
                workdir=os.path.abspath(
                    os.path.join(os.path.dirname(path), data['parameters'].get('workdir', '../..'))),
                loop=data['parameters'].get('loop', False)
            )
        else:
            return None


@dataclass
class BaseTrafficConfig:
    duration: int


@dataclass
class TrafficSequenceConfig:
    sequence: list[BaseTrafficConfig]


@dataclass
class OverlapTrafficConfig:
    overlaps: list[tuple[int, BaseTrafficConfig]]  # (Offset, Config)


@dataclass
class PeriodicTrafficConfig(BaseTrafficConfig):
    packet_size: int  # Bytes
    interval: int  # ms

    @classmethod
    def from_dict(cls, source: dict):
        return PeriodicTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            packet_size=_parse_bytes(source.get('size', '1kB')),
            interval=parse_time(source.get('interval', '100ms'))
        )


@dataclass
class RandomTrafficConfig(BaseTrafficConfig):
    min_size: int  # Bytes
    max_size: int  # Bytes

    @classmethod
    def from_dict(cls, source: dict):
        return RandomTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            min_size=_parse_bytes(source.get('min_size', '1kB')),
            max_size=_parse_bytes(source.get('max_size', '1kB'))
        )


class DistributionType(Enum):
    normal = 'normal-distribution'
    uniform = 'uniform-distribution'
    exponential = 'exponential-distribution'


@dataclass
class DistributedTrafficConfig(BaseTrafficConfig):
    cumulative_size: int  # Bytes
    distribution: DistributionType
    # Normal distribution parameters
    mean: Optional[float] = None
    variance: Optional[float] = None
    # Exponential distribution parameters
    lambda_: Optional[float] = None
    reverse: Optional[bool] = None

    @classmethod
    def from_dict(cls, source: dict):
        return DistributedTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            cumulative_size=_parse_bytes(source.get('cumulative_size', '1kB')),
            distribution=DistributionType(source.get('type', 'normal-distribution')),

            mean=source.get('mean'),
            variance=source.get('variance'),

            lambda_=source.get('lambda'),
            reverse=source.get('reverse')
        )


@dataclass
class Pause(BaseTrafficConfig):
    @classmethod
    def from_duration(cls, duration):
        return Pause(duration=parse_time(duration))
