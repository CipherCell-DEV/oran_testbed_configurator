import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from model.utils_config import BuildType


class CoreImplementation(Enum):
    OPEN5GS = "open5gs"
    OPEN5GS_SRS = "open5gs_srs"


# TODO single enum
ALLOWED_IMPLEMENTATION_LIST = {'Open5GS': CoreImplementation.OPEN5GS, 'Open5GS_SRS': CoreImplementation.OPEN5GS_SRS}


@dataclass
class Core5GNetworkCfg:
    ip: Optional[ipaddress.IPv4Address] = None
    mongodb_ip: Optional[ipaddress.IPv4Address] = None
    subnet: Optional[ipaddress.IPv4Network] = None

    def __str__(self):
        return (
            f"Core5GNetworkCfg:\n"
            f"    ip={self.ip}\n"
            f"    mongodb_ip={self.mongodb_ip}\n"
            f"    network={self.subnet}\n"
        )


@dataclass
class Core5GCfg:
    implementation: Optional[CoreImplementation] = None
    build_type: BuildType = BuildType.DOCKER
    commit: str = "latest"
    repository : str = ""
    network: Optional[Core5GNetworkCfg] = None

    def __str__(self):
        return (f"Core5GCfg: \n"
                f"    build_type={self.implementation},\n"
                f"    repository={self.repository},\n"
                f"    commit={self.commit},\n"
                f"    build_type={self.build_type},\n"
                f"    network=\n{self.network}")


class CoreFieldIdentifiers:
    IP_ADDR = '5gc_ip'
    NETWORK = 'network'
    SUBNET = 'subnet'
    CORE_IP = '5gc_ip'
    MONGO_DB_IP = 'mongo_db_ip'
