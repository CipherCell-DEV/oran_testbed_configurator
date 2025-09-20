import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CoreImplementation(Enum):
    SRS = 0


@dataclass
class Core5GCfg:
    ip: Optional[ipaddress.IPv4Address] = None
    network: Optional[ipaddress.IPv4Network] = None
    implementation: Optional[CoreImplementation] = None

    def __str__(self):
        return (f"Core5GCfg: \n"
                f"    ip={self.ip}, \n"
                f"    network={self.network}")


class CoreFieldIdentifiers:
    IMPLEMENTATION = 'implementation'
    IP_ADDR = 'ip_addr'
    SUBNET = 'subnet'
