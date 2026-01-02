import ipaddress
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from model.gnb_config import DefaultValuesGNB
from model.utils_config import BuildType


class UEImplementation(Enum):
    SRS_4G = 'srs_4g'


class USIMMode(Enum):
    SOFT = "soft"
    HARD = "hard"


class USIMAlgo(Enum):
    MILENAGE = "milenage"
    XOR = "xor"
    COMP = "comp"
    COMP128_1 = "comp128_1"
    COMP128_2 = "comp128_2"
    COMP128_3 = "comp128_3"


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
    key: Optional[str] = None
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
                f"    key={self.key}, \n"
                f"    k2={self.k2}, \n"
                f"    k3={self.k3}, \n"
                f"    imsi={self.imsi}, \n"
                f"    imsi2={self.imsi2}, \n"
                f"    imei={self.imei}, \n")


@dataclass
class UEInstCfg:
    implementation: Optional[UEImplementation] = None
    repository : Optional[str] = None
    commit: str = "latest"
    name: Optional[str] = None
    build_type : BuildType = BuildType.DOCKER
    ip: Optional[ipaddress.IPv4Address] = None
    srate: Optional[int] = None
    usim: Optional[USIMCfg] = None
    gateway: Optional[UEGatewayCfg] = None

    def __str__(self):
        return (f"UECfg: \n"
                f"    implementation={self.implementation}, \n"
                f"    repository={self.repository}, \n"
                f"    commit={self.commit}, \n"
                f"    name={self.name}, \n"
                f"    build_type={self.build_type}, \n"
                f"    ip={self.ip}, \n"
                f"    srate={self.srate}, \n"
                f"    usim={self.usim}, \n"
                f"    gateway={self.gateway}")


@dataclass
class UECfg:
    ip_range: Optional[ipaddress.IPv4Address] = None
    gateway: Optional[ipaddress.IPv4Network] = None
    ues: List[UEInstCfg] = field(default_factory=list)

    def __str__(self):
        ues_str = "\n".join(f"  {ue}" for ue in self.ues) if self.ues else "  None"
        return (
            f"UECfg:\n"
            f"    ip_range={self.ip_range}\n"
            f"    gateway={self.gateway}\n"
            f"    ues:\n{ues_str}"
        )


class USIMFieldIdentifiers:
    MODE = "mode"
    ALGO = 'algo'
    OPC = 'opc'
    KEY = 'key'
    IMSI = 'imsi'
    IMEI = 'imei'


class GatewayFieldIdentifiers:
    NETNS = 'netns'
    IP_DEVNAME = 'ip_devname'
    IP_NETMASK = 'ip_netmask'


class UEFieldIdentifiers:
    IMPLEMENTATION = 'implementation'
    BUILD_TYPE = 'build_type'
    IP_ADDR = 'ip_addr'
    SRATE = 'srate'
    GATEWAY = 'gateway'
    USIM = 'usim'
    USIM_FIELD_IDENTIFIERS = USIMFieldIdentifiers()
    GATEWAY_IDENTIFIERS = GatewayFieldIdentifiers()
    IP_RANGE = 'ip_range'


class DefaultValuesUE:
    DEFAULT_UE_NETNS = "ue1"
    DEFAULT_UE_GW_DEVNAME = "tun_srsue"
    DEFAULT_SRATE = DefaultValuesGNB.DEFAULT_SRATE


SRSRAN_4G_UE_DEPENDENCIES_LINUX = ['build-essential', 'cmake', 'pkg-config', 'libfftw3-dev',
                                   'libzmq3-dev', 'libmbedtls-dev', 'libsoapysdr-dev', 'soapysdr-tools',
                                   'libboost-all-dev', 'libsctp-dev', 'lksctp-tools', 'libconfig++-dev', 'iproute2']
