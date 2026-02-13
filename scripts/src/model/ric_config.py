from __future__ import annotations
import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from model.utils_config import BuildType


class RICImplementation(Enum):
    ORAN_SC_RIC = "oran_sc_ric"
    FLEX_RIC = "flexric"


class RICRelease(Enum):
    RELEASE_i = 'i'
    RELEASE_j = 'j'
    RELEASE_k = 'k'
    RELEASE_l = 'l'
    RELEASE_m = 'm'

    def __str__(self):
        return str(self.value)

    @staticmethod
    def get_version_from_field_identifier(field_identifier: str) -> RICRelease:
        try:
            return RICRelease(field_identifier.lower())
        except ValueError as exc:
            raise ValueError(
                f"Unsupported RIC Release field identifier: {field_identifier}"
            ) from exc

    @staticmethod
    def lookup_subversion(release: RICRelease) -> dict:
        match release:
            case RICRelease.RELEASE_i:
                return {
                    'e2term_ver': '6.0.4',
                    'e2mgr_ver': '6.0.4',
                    'dbaas_ver': '0.6.4',
                    'submgr_ver': '0.10.1',
                    'appmgr_ver': '0.5.7',
                    'a1_ver': '3.2.2',
                }

            case RICRelease.RELEASE_j:
                return {
                    'e2term_ver': '6.0.6',
                    'e2mgr_ver': '6.0.6',
                    'dbaas_ver': '0.6.4',
                    'submgr_ver': '0.10.2',
                    'appmgr_ver': '0.5.8',
                    'a1_ver': '3.2.2',
                }

            case RICRelease.RELEASE_k:
                return {
                    'e2term_ver': '6.0.6',
                    'e2mgr_ver': '6.0.6',
                    'dbaas_ver': '0.6.4',
                    'submgr_ver': '0.10.2',
                    'appmgr_ver': '0.5.8',
                    'a1_ver': '3.2.2',
                }

            case RICRelease.RELEASE_l:
                return {
                    'e2term_ver': '6.0.6',
                    'e2mgr_ver': '6.0.6',
                    'dbaas_ver': '0.6.4',
                    'submgr_ver': '0.10.2',
                    'appmgr_ver': '0.5.8',
                    'a1_ver': '3.2.2',
                }

            case RICRelease.RELEASE_m:
                return {
                    'e2term_ver': '6.0.7',
                    'e2mgr_ver': '6.0.7',
                    'dbaas_ver': '0.6.5',
                    'submgr_ver': '0.10.3',
                    'appmgr_ver': '0.5.9',
                    'a1_ver': '3.2.3',
                }
        raise ValueError(f"Unsupported RIC Release: {release}")


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
    implementation: Optional[RICImplementation] = None
    repository: str = ""
    commit: str = "latest"
    release: Optional[RICRelease] = None
    build_type: BuildType = BuildType.DOCKER
    ip_config: Optional[NearRTRICNetworkConfig] = None

    def __str__(self):
        return (f"NearRtRICCFG: \n"
                f"    implementation={self.implementation}, \n"
                f"    repository={self.repository}, \n"
                f"    commit={self.commit}, \n"
                f"    release={self.release}, \n"
                f"    build_type={self.build_type}, \n"
                f"{self.ip_config}")


class RICFieldIdentifiers:
    RELEASE = 'release'
    NETWORK = 'network'


class DefaultValuesRIC:
    DEFAULT_RELEASE = RICRelease.RELEASE_i
    DEFAULT_NETWORK_CONFIG = {
        'subnet': ipaddress.IPv4Network('10.0.2.0/24'),
        'dbaas_ip': ipaddress.IPv4Address('10.0.2.12'),
        'e2term_ip': ipaddress.IPv4Address('10.0.2.10'),
        'e2mgr_ip': ipaddress.IPv4Address('10.0.2.11'),
        'submgr_ip': ipaddress.IPv4Address('10.0.2.14'),
        'rtmgr_sim_ip': ipaddress.IPv4Address('10.0.2.15'),
        'xapp_runner_ip': ipaddress.IPv4Address('10.0.2.20')
    }
