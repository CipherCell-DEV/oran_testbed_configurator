import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import yaml


def parse_time(timestr: str) -> int:
    """Parse a time string like '10s', '2m', '1h', '1.5m', '10ms' into milliseconds (int)."""
    match = re.match(r"(\d+(?:\.\d+)?)[ ]*(ms|s|m|h)", timestr.strip())
    if not match:
        raise ValueError(f"Invalid time format: {timestr}")
    value, unit = match.groups()
    value = int(value)
    if unit == 'ms':
        return value
    elif unit == 's':
        return value * 1000
    elif unit == 'm':
        return value * 60 * 1000
    elif unit == 'h':
        return value * 3600 * 1000
    else:
        raise ValueError(f"Unknown time unit: {unit}")


def parse_bytes(timestr: str) -> int:
    """Parse a byte size string like '10B', '2kB', '1MB', '1.5GB' into Bytes (int)."""
    match = re.match(r"(\d+(?:\.\d+)?)[ ]*(B|kB|MB|GB)", timestr.strip())
    if not match:
        raise ValueError(f"Invalid size format: {timestr}")
    value, unit = match.groups()
    value = int(value)
    if unit == 'B':
        return value
    elif unit == 'kB':
        return value * 1_000
    elif unit == 'MB':
        return value * 1_000_000
    elif unit == 'GB':
        return value * 1_000_000_000
    else:
        raise ValueError(f"Unknown unit: {unit}")


@dataclass
class TrafficParameters:
    granularity: int  # milliseconds
    gnb_address: str  # IP Address
    ue_address: str  # IP Address
    workdir: str  # Path to docker-compose.yaml
    loop: bool

    @classmethod
    def from_yaml(cls, path: str) -> Optional['TrafficParameters']:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'parameters' in data:
            return TrafficParameters(
                granularity=parse_time(data['parameters'].get('granularity', '100ms')),
                gnb_address=data['parameters'].get('gnb-address', '10.45.1.1'),
                ue_address=data['parameters'].get('ue-address', '10.45.1.2'),
                workdir=os.path.abspath(os.path.join(os.path.dirname(path), data['parameters'].get('workdir', '../..'))),
                loop=data['parameters'].get('loop', False)
            )
        else:
            return None


@dataclass
class AtomicTrafficConfig:
    duration: int


@dataclass
class TrafficSequenceConfig:
    sequence: list[AtomicTrafficConfig]


@dataclass
class OverlapTrafficConfig:
    overlaps: list[tuple[int, AtomicTrafficConfig]]  # (Offset, Config)


@dataclass
class PeriodicTrafficConfig(AtomicTrafficConfig):
    packet_size: int  # Bytes
    interval: int  # ms

    @classmethod
    def from_dict(cls, source: dict):
        return PeriodicTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            packet_size=parse_bytes(source.get('size', '1kB')),
            interval=parse_time(source.get('interval', '100ms'))
        )


@dataclass
class RandomTrafficConfig(AtomicTrafficConfig):
    min_size: int  # Bytes
    max_size: int  # Bytes

    @classmethod
    def from_dict(cls, source: dict):
        return RandomTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            min_size=parse_bytes(source.get('min_size', '1kB')),
            max_size=parse_bytes(source.get('max_size', '1kB'))
        )


class DistributionType(Enum):
    normal = 'normal-distribution'
    uniform = 'uniform-distribution'
    exponential = 'exponential-distribution'


@dataclass
class DistributedTrafficConfig(AtomicTrafficConfig):
    cumulative_size: int  # Bytes
    distribution: DistributionType

    @classmethod
    def from_dict(cls, source: dict):
        return DistributedTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            cumulative_size=parse_bytes(source.get('cumulative_size', '1kB')),
            distribution=DistributionType(source.get('type', 'normal-distribution'))
        )


@dataclass
class Pause(AtomicTrafficConfig):
    @classmethod
    def from_dict(cls, source):
        return Pause(duration=parse_time(source.get('duration', '0ms')))


def from_dict(source: dict):
    t_type = next(iter(source.keys()))

    match t_type:
        case 'overlap':
            config = OverlapTrafficConfig([])
            for item in source['overlap']:
                traffic_key = next(k for k in ('periodic', 'random', 'distribution', 'loop') if k in item)
                offset = parse_time(item[traffic_key]['offset'])
                config.overlaps.append((offset, from_dict(item)))
            return config
        case 'pause':
            return Pause.from_dict(source['pause'])
        case 'periodic':
            return PeriodicTrafficConfig.from_dict(source['periodic'])
        case 'random':
            return RandomTrafficConfig.from_dict(source['random'])
        case 'distribution':
            return DistributedTrafficConfig.from_dict(source['distribution'])
        case 'loop':
            source = source['loop']
            god = TrafficSequenceConfig([])
            for config in source['elements']:
                god.sequence.append(from_dict(config))
            god.sequence *= source['iterations']
            return god
        case _:
            print(f'Unknown traffic type: {t_type}')
            return None


def from_yaml(path: str) -> Optional['TrafficSequenceConfig']:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    if 'traffic' not in data:
        print('Config file needs to contain traffic config!')
        return None
    god = TrafficSequenceConfig([])
    for part in data['traffic']:
        god.sequence.append(from_dict(part))
    return god
