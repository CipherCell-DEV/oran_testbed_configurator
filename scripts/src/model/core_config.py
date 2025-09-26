import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from model.utils_config import BuildType


class CoreImplementation(Enum):
    SRS = 0


ALLOWED_IMPLEMENTATION_LIST = {'srs': CoreImplementation.SRS}


@dataclass
class Core5GCfg:
    ip: Optional[ipaddress.IPv4Address] = None
    network: Optional[ipaddress.IPv4Network] = None
    implementation: Optional[CoreImplementation] = None
    build_type = BuildType = BuildType.DOCKER

    def __str__(self):
        return (f"Core5GCfg: \n"
                f"    build_type={self.build_type}"
                f"    ip={self.ip}, \n"
                f"    network={self.network}")


class CoreFieldIdentifiers:
    IP_ADDR = 'ip_addr'
    SUBNET = 'subnet'
