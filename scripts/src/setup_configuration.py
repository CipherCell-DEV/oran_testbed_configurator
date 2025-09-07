from dataclasses import dataclass, is_dataclass
from enum import Enum
from pprint import pformat
from typing import List, Optional, Any
import ipaddress


class BuildType(Enum):
    LOCAL = 0
    DOCKER = 1


class RICImplementation(Enum):
    ORAN_SC_RIC = 0
    FLEX_RIC = 1


class RICRelease(Enum):
    RELEASE_i = 0,
    RELEASE_l = 1


@dataclass
class NearRTRICNetworkConfig:
    subnet: Optional[ipaddress.IPv4Network] = None
    dbaas_ip: Optional[ipaddress.IPv4Address] = None
    e2term_ip: Optional[ipaddress.IPv4Address] = None
    e2mgr_ip: Optional[ipaddress.IPv4Address] = None
    submgr_ip: Optional[ipaddress.IPv4Address] = None
    appmgr_ip: Optional[ipaddress.IPv4Address] = None
    rtmgr_sim_ip: Optional[ipaddress.IPv4Address] = None
    xapp_runner_ip: Optional[ipaddress.IPv4Address] = None

    def __str__(self):
        return (f"  NearRTRICNetworkConfig: \n"
                f"      subnet={self.subnet}, \n"
                f"      dbaas_ip={self.dbaas_ip}, \n"
                f"      e2term_ip={self.e2term_ip}, \n"
                f"      e2mgr_ip={self.e2mgr_ip}, \n"
                f"      submgr_ip={self.submgr_ip}, \n"
                f"      appmgr_ip={self.appmgr_ip}, \n"
                f"      rtmgr_sim_ip={self.rtmgr_sim_ip}, \n"
                f"      xapp_runner_ip={self.xapp_runner_ip}")


@dataclass
class NearRtRICCFG:
    type: Optional[RICImplementation] = None
    release: Optional[RICRelease] = None
    ip_config: Optional[NearRTRICNetworkConfig] = None

    def __str__(self):
        return (f"NearRtRICCFG: \n"
                f"    type={self.type}, \n"
                f"    release={self.release}, \n"
                f"{self.ip_config}")


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


class GNBType(Enum):
    SRS = 1


@dataclass
class GNBCfg:
    type: Optional[GNBType] = None
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
                f"    imei={self.imei}, \n"
                f"{self.gw}")


@dataclass
class UECfg:
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


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class EnvironmentCfg:
    build_type: Optional[BuildType] = None
    log_level: Optional[LogLevel] = None
    log_dir: Optional[str] = None
    build_dir: Optional[str] = None

    def __str__(self):
        return (f"EnvironmentCfg: \n"
                f"    build_type={self.build_type}, \n"
                f"    log_level={self.log_level}, \n"
                f"    log_dir={self.log_dir}, \n"
                f"    build_dir={self.build_dir}")


class SetupConfiguration:
    environment: Optional[EnvironmentCfg] = None
    build_type = BuildType = BuildType.DOCKER
    near_rt_ric: Optional[NearRtRICCFG] = None
    core_5g: Core5GCfg
    gnb: Optional[GNBCfg] = None
    ue: List[UECfg] = []

    def __str__(self):
        return (f"SetupConfiguration: \n"
                f"{self.environment}, \n"
                f"{self.near_rt_ric}, \n"
                f"{self.core_5g}, \n"
                f"{self.gnb}, \n"
                f"UECfgs: \n"
                f"{pformat(self.ue, indent=4)}")
