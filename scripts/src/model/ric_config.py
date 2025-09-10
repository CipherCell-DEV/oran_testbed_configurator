import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RICImplementation(Enum):
    ORAN_SC_RIC = 0
    FLEX_RIC = 1


class RICRelease(Enum):
    RELEASE_i = 0,
    RELEASE_l = 1


ORAN_SC_RIC_SERVICE_IP_MAP = {
    "dbaas": ("DBAAS_IP", "dbaas_ip"),
    "rtmgr_sim": ("RTMGR_SIM_IP", "rtmgr_sim_ip"),
    "submgr": ("SUBMGR_IP", "submgr_ip"),
    "e2term": ("E2TERM_IP", "e2term_ip"),
    "appmgr": ("APPMGR_IP", "appmgr_ip"),
    "e2mgr": ("E2MGR_IP", "e2mgr_ip"),
    "python_xapp_runner": ("XAPP_PY_RUNNER_IP", "xapp_runner_ip"),
}


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
