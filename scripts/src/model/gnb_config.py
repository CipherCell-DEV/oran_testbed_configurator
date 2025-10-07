import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from model.utils_config import BuildType


class GNBImplementation(Enum):
    SRS = 1


ALLOWED_IMPLEMENTATION_LIST = {'srs': GNBImplementation.SRS}


@dataclass
class GNBIPConfig:
    e2: Optional[ipaddress.IPv4Address] = None
    ru_sdr: Optional[ipaddress.IPv4Address] = None
    cu_cp: Optional[ipaddress.IPv4Address] = None

    def __str__(self):
        return (f"  GNBIPConfig: \n"
                f"      e2={self.e2}, \n"
                f"      ru_sdr={self.ru_sdr}, \n"
                f"      cu_cp={self.cu_cp}")


@dataclass
class GNBCfg:
    implementation: Optional[GNBImplementation] = None
    commit: str = "latest"
    build_type = BuildType = BuildType.DOCKER
    ip_config: Optional[GNBIPConfig] = None
    srate: Optional[float] = 11.52
    tx_gain: Optional[int] = 75
    rx_gain: Optional[int] = 75

    def __str__(self):
        return (f"GNBCfg: \n"
                f"    implementation={self.implementation}, \n"
                f"    commit={self.commit}, \n"
                f"    ip={self.ip_config}, \n"
                f"    srate={self.srate}, \n"
                f"    tx_gain={self.tx_gain}, \n"
                f"    rx_gain={self.rx_gain}")


class GnbFieldIdentifiers:
    SRATE = 'srate'
    IP_ADDR = 'ip_addr'
    GNB_TYPE = 'type'
    TX_GAIN = 'tx_gain'
    RX_GAIN = 'rx_gain'


class DefaultValuesGNB:
    DEFAULT_SRATE = 11.52e6
    TX_GAIN = 75
    RX_GAIN = 75


SRSRAN_GNB_DEPENDENCIES_LINUX = ['build-essential', 'cmake', 'libdw-dev', 'binutils-dev', 'libdwarf-dev', 'libelf-dev',
                                 'pkg-config', 'libfftw3-dev', 'libyaml-cpp-dev', 'libmbedtls-dev', 'libsctp-dev',
                                 'libzmq3-dev', 'libzmq5']
