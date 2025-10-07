from typing import Optional

import yaml

from model.traffic.traffic_config import TrafficSequenceConfig, OverlapTrafficConfig, Pause, PeriodicTrafficConfig, \
    RandomTrafficConfig, DistributedTrafficConfig, parse_time


class TrafficConfigParser:

    @staticmethod
    def load_yaml(path: str) -> Optional['TrafficSequenceConfig']:
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        if 'traffic' not in data:
            print('Config file needs to contain traffic config!')
            return None
        god = TrafficSequenceConfig([])
        for part in data['traffic']:
            god.sequence.append(TrafficConfigParser.__parse_dict(part))
        return god

    @staticmethod
    def __parse_dict(source: dict):
        t_type = next(iter(source.keys()))

        match t_type:
            case 'overlap':
                config = OverlapTrafficConfig([])
                for item in source['overlap']:
                    if 'offset' in item:
                        continue
                    key = next(
                        k for k in ('periodic', 'random', 'distribution', 'loop', 'overlap', 'pause') if k in item)
                    if key == 'overlap':
                        offset = next((k['offset'] for k in item[key] if 'offset' in k), '0ms')
                    else:
                        offset = item[key].get('offset', '0s')

                    config.overlaps.append((parse_time(offset), TrafficConfigParser.__parse_dict(item)))
                return config
            case 'pause':
                return Pause.from_duration(source['pause'])
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
                    god.sequence.append(TrafficConfigParser.__parse_dict(config))
                god.sequence *= source['iterations']
                return god
            case _:
                print(f'Unknown traffic type: {t_type}')
                return None
