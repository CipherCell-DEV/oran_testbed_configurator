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
class BaseTrafficConfig:
    granularity: int  # milliseconds
    gnb_address: str  # IP Address
    ue_address: str  # IP Address
    workdir: str  # Path to docker-compose.yaml

    @classmethod
    def from_yaml(cls, path: str) -> Optional['BaseTrafficConfig']:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'traffic' in data and 'periodic' in data['traffic']:
            return BaseTrafficConfig(
                granularity=parse_time(data['traffic'].get('granularity', '100ms')),
                gnb_address=data['traffic'].get('gnb-address', '10.45.1.1'),
                ue_address=data['traffic'].get('ue-address', '10.45.1.2'),
                workdir=os.path.abspath(os.path.join(os.path.dirname(path), data['traffic'].get('workdir', '../..')))
            )
        else:
            return None


@dataclass
class PeriodicTrafficConfig(BaseTrafficConfig):
    packet_size: int  # Bytes  TODO: Turn into kB
    interval: int  # ms
    duration: int  # ms

    @classmethod
    def from_yaml(cls, path: str) -> Optional['PeriodicTrafficConfig']:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'traffic' in data and 'periodic' in data['traffic']:
            periodic_config = data['traffic']['periodic']
            base_config = BaseTrafficConfig.from_yaml(path)
            return PeriodicTrafficConfig(
                granularity=base_config.granularity,
                gnb_address=base_config.gnb_address,
                ue_address=base_config.ue_address,
                workdir=base_config.workdir,

                packet_size=int(periodic_config.get('size', 1)),
                interval=parse_time(periodic_config.get('interval', '100ms')),
                duration=parse_time(periodic_config.get('duration', '1s'))
            )
        else:
            return None
