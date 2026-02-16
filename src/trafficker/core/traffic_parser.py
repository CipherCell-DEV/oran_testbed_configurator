"""
YAML configuration parser for traffic patterns.

Parses traffic configuration files and converts them into TrafficConfig objects.
"""

from trafficker.model.traffic_config import *
from trafficker.model.traffic_type import TrafficType


class TrafficConfigParser:
    """Parser for YAML traffic configuration files."""

    @staticmethod
    def load_yaml(path: str) -> dict:
        """
        Load and parse traffic configurations from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            Dictionary mapping UE IDs to TrafficSequenceConfigs
        """
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'traffic' not in data:
            print('Config file needs to contain traffic config!')
            return {}
        traffic_by_ue = {}
        for ue_id, traffic in data['traffic'].items():
            for part in traffic:
                if ue_id not in traffic_by_ue:
                    traffic_by_ue[ue_id] = TrafficSequenceConfig([])
                traffic_by_ue[ue_id].sequence.append(TrafficConfigParser.__parse_dict(part))
        return traffic_by_ue

    @staticmethod
    def __parse_dict(source: dict):
        """
        Recursively parse traffic configuration dictionary.

        Args:
            source: Dictionary containing traffic pattern configuration

        Returns:
            Appropriate TrafficConfig subclass instance
        """

        try:
            traffic_type = TrafficType(next(iter(source.keys())))
        except ValueError:
            print(f'Unknown traffic type: {traffic_type}')
            return None

        match traffic_type:
            case TrafficType.OVERLAP:
                config = OverlapTrafficConfig([])
                for item in source[TrafficType.OVERLAP.value]:
                    if 'offset' in item:
                        continue
                    key = next((t.value for t in TrafficType if t.value in item), None)
                    if key == TrafficType.OVERLAP.value:
                        offset = next((k['offset'] for k in item[key] if 'offset' in k), '0ms')
                    else:
                        offset = item[key].get('offset', '0s')

                    config.overlaps.append((parse_time(offset), TrafficConfigParser.__parse_dict(item)))
                return config
            case TrafficType.PAUSE:
                return Pause.from_duration(source[TrafficType.PAUSE.value])
            case TrafficType.PERIODIC:
                return PeriodicTrafficConfig.from_dict(source[TrafficType.PERIODIC.value])
            case TrafficType.RANDOM:
                return RandomTrafficConfig.from_dict(source[TrafficType.RANDOM.value])
            case TrafficType.DISTRIBUTION:
                return DistributedTrafficConfig.from_dict(source[TrafficType.DISTRIBUTION.value])
            case TrafficType.LOOP:
                loop_config = source[TrafficType.LOOP.value]
                sequence = TrafficSequenceConfig([])
                for config in loop_config['elements']:
                    sequence.sequence.append(TrafficConfigParser.__parse_dict(config))
                sequence.sequence *= loop_config['iterations']
                return sequence
