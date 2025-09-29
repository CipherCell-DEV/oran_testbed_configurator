import os
import re
from dataclasses import dataclass
from typing import Optional

import yaml


def parse_time(timestr: str) -> int:
    """Parse a time string like '10s', '2m', '1h', '1.5m', '10ms' into seconds (float)."""
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


@dataclass
class TrafficParameters:
    granularity: int  # milliseconds
    gnb_address: str  # IP Address
    ue_address: str  # IP Address
    workdir: str  # Path to docker-compose.yaml

    @classmethod
    def from_yaml(cls, path: str) -> Optional['TrafficParameters']:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'parameters' in data:
            return TrafficParameters(
                granularity=parse_time(data['parameters'].get('granularity', '100ms')),
                gnb_address=data['parameters'].get('gnb-address', '10.45.1.1'),
                ue_address=data['parameters'].get('ue-address', '10.45.1.2'),
                workdir=os.path.abspath(os.path.join(os.path.dirname(path), data['parameters'].get('workdir', '../..')))
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
    packet_size: int  # Bytes  TODO: Turn into kB
    interval: int  # ms

    @classmethod
    def from_dict(cls, source: dict):
        return PeriodicTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            packet_size=int(source.get('size', 1)),
            interval=parse_time(source.get('interval', '100ms'))
        )

@dataclass
class RandomTrafficConfig(AtomicTrafficConfig):
    min_size: int  # Bytes  TODO: Turn into kB
    max_size: int  # Bytes  TODO: Turn into kB

    @classmethod
    def from_dict(cls, source: dict):
        return RandomTrafficConfig(
            duration=parse_time(source.get('duration', '1s')),
            min_size=int(source.get('min_size', 1)),
            max_size=int(source.get('max_size', 1))
        )


@dataclass
class Pause(AtomicTrafficConfig):
    @classmethod
    def from_dict(cls, source):
        return Pause(duration=parse_time(source.get('duration', '0ms')))


def from_yaml(path: str) -> Optional['TrafficSequenceConfig']:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    if 'traffic' not in data:
        print('Config file needs to contain traffic config!')
        return
    data = data['traffic']
    god = TrafficSequenceConfig([])
    for part in data:
        if 'overlap' in part:
            overlap_god = OverlapTrafficConfig([])
            for config in part['overlap']:
                if 'periodic' in config:
                    offset = parse_time(config['periodic']['offset'])
                    parsed_config = PeriodicTrafficConfig.from_dict(config['periodic'])
                    overlap_god.overlaps.append((offset, parsed_config))
                if 'random' in config:
                    offset = parse_time(config['random']['offset'])
                    parsed_config = RandomTrafficConfig.from_dict(config['random'])
                    overlap_god.overlaps.append((offset, parsed_config))
            god.sequence.append(overlap_god)
        elif 'pause' in part:
            god.sequence.append(Pause.from_dict(part['pause']))
        elif 'periodic' in part:
            god.sequence.append(PeriodicTrafficConfig.from_dict(part['periodic']))
        elif 'random' in part:
            god.sequence.append(RandomTrafficConfig.from_dict(part['random']))
    return god
