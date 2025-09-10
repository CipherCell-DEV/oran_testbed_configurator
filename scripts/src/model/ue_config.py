import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from model.utils_config import BuildType


class UEImplementation(Enum):
    SRS_4G = 0


class USIMMode(Enum):
    SOFT = 0
    HARD = 1


class USIMAlgo(Enum):
    MILENAGE = 0
    XOR = 1
    COMP = 2
    COMP128_1 = 3
    COMP128_2 = 4
    COMP128_3 = 5


@dataclass
class UEGatewayCfg:
    netns: Optional[str] = None
    ip_devname: Optional[str] = None
    ip_netmask: Optional[ipaddress.IPv4Network] = None

    def __str__(self):
        return (f"  UEGatewayCfg: \n"
                f"      netns={self.netns}, \n"
                f"      ip_devname={self.ip_devname}, \n"
                f"      ip_netmask={self.ip_netmask}")


@dataclass
class USIMCfg:
    mode: Optional[USIMMode] = None
    algo: Optional[USIMAlgo] = None
    opc: Optional[str] = None
    opc_value: Optional[str] = None
    k: Optional[str] = None
    k2: Optional[str] = None
    k3: Optional[str] = None
    imsi: Optional[str] = None
    imsi2: Optional[str] = None
    imei: Optional[str] = None

    def __str__(self):
        return (f"USIMCfg: \n"
                f"    mode={self.mode}, \n"
                f"    algo={self.algo}, \n"
                f"    opc={self.opc}, \n"
                f"    opc_value={self.opc_value}, \n"
                f"    k={self.k}, \n"
                f"    k2={self.k2}, \n"
                f"    k3={self.k3}, \n"
                f"    imsi={self.imsi}, \n"
                f"    imsi2={self.imsi2}, \n"
                f"    imei={self.imei}, \n")


@dataclass
class UECfg:
    implementation: Optional[UEImplementation] = None
    name: Optional[str] = None
    build_type = BuildType = BuildType.DOCKER
    ip: Optional[ipaddress.IPv4Address] = None
    srate: Optional[int] = None
    usim: Optional[USIMCfg] = None
    gateway: Optional[UEGatewayCfg] = None

    def __str__(self):
        return (f"UECfg: \n"
                f"    name={self.name}, \n"
                f"    build_type={self.build_type}, \n"
                f"    ip={self.ip}, \n"
                f"    srate={self.srate}, \n"
                f"{self.usim}")
