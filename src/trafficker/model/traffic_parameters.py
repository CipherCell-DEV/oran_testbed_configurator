"""Module for defining and loading traffic generation parameters from a YAML configuration file."""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import yaml

from trafficker.model.utils import parse_time


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
                direction=Direction(data['parameters'].get('direction', 'DL')),
                workdir=os.path.abspath(
                    os.path.join(os.path.dirname(path), data['parameters'].get('workdir', '..'))),
                loop=data['parameters'].get('loop', False),
                use_nist=data['parameters'].get('use_nist', False),
                nist_vm=data['parameters'].get('nist_vm_ssh', 'local'),
                use_udp=data['parameters'].get('use_udp', False),
            )
        else:
            return None
