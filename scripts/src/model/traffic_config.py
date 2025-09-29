import yaml
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class PeriodicTrafficConfig:
    size: int
    interval: int # milliseconds
    duration: int # milliseconds

@dataclass
class TrafficConfig:
    periodic: Optional[PeriodicTrafficConfig] = None

    @staticmethod
    def parse_time(timestr: str) -> float:
        """Parse a time string like '10s', '2m', '1h', '1.5m', '10ms' into seconds (float)."""
        match = re.match(r"(\d+(?:\.\d+)?)[ ]*(ms|s|m|h)", timestr.strip())
        if not match:
            raise ValueError(f"Invalid time format: {timestr}")
        value, unit = match.groups()
        value = float(value)
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

    @classmethod
    def from_yaml(cls, path: str) -> 'TrafficConfig':
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        periodic = None
        if 'traffic' in data and 'periodic' in data['traffic']:
            p = data['traffic']['periodic']
            periodic = PeriodicTrafficConfig(
                size=int(p.get('size', 1)),
                interval=cls.parse_time(p.get('interval', '1s')),
                duration=cls.parse_time(p.get('duration', '1s'))
            )
        return cls(periodic=periodic)
