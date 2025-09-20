import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from model.utils_config import BuildType


class GNBImplementation(Enum):
    SRS = 1


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
    type: Optional[GNBImplementation] = None
    build_type = BuildType = BuildType.DOCKER
    ip_config: Optional[GNBIPConfig] = None
    srate: Optional[float] = 11.52
    tx_gain: Optional[int] = 75
    rx_gain: Optional[int] = 75

    def __str__(self):
        return (f"GNBCfg: \n"
                f"    type={self.type}, \n"
                f"{self.ip_config}, \n"
                f"    srate={self.srate}, \n"
                f"    tx_gain={self.tx_gain}, \n"
                f"    rx_gain={self.rx_gain}")


class GnbFieldIdentifiers:
    SRATE = 'srate'
    IP_ADDR = 'ip_addr'
    GNB_TYPE = 'type'
    TX_GAIN = 'tx_gain'
    RX_GAIN = 'rx_gain'
    BUILD_TYPE = 'build_type'


class DefaultValuesGNB:
    DEFAULT_SRATE = 11.52e6
    TX_GAIN = 75
    RX_GAIN = 75