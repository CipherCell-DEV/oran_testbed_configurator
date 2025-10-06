import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from model.utils_config import BuildType


class CoreImplementation(Enum):
    OPEN5GS = 0
    OPEN5GS_SRS = 1


ALLOWED_IMPLEMENTATION_LIST = {'Open5GS': CoreImplementation.OPEN5GS, 'Open5GS_SRS': CoreImplementation.OPEN5GS_SRS}


@dataclass
class Core5GCfg:
    implementation: Optional[CoreImplementation] = None
    build_type: BuildType = BuildType.DOCKER
    commit: str = "latest"
    ip: Optional[ipaddress.IPv4Address] = None
    network: Optional[ipaddress.IPv4Network] = None

    def __str__(self):
        return (f"Core5GCfg: \n"
                f"    build_type={self.implementation},\n"
                f"    commit={self.commit},\n"
                f"    build_type={self.build_type},\n"
                f"    ip={self.ip},\n"
                f"    network={self.network}")


class CoreFieldIdentifiers:
    IP_ADDR = 'ip_addr'
    SUBNET = 'subnet'
