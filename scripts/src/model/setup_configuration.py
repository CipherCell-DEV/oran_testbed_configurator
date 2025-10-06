from pprint import pformat
from typing import List, Optional

from model.core_config import Core5GCfg
from model.gnb_config import GNBCfg
from model.ric_config import NearRtRICCFG
from model.ue_config import UECfg
from model.utils_config import LogLevel


class ComponentIdentifiers:
    CFG_NEAR_RT_RIC = "near_rt_ric"
    CFG_5GC = "5gc"
    CFG_UE = "ue"
    CFG_GNB = "gnb"
    CFG_ENVIRONMENT = "environment"


class GeneralIdentifiers:
    BUILD_TYPE = 'build_type'
    IMPLEMENTATION = 'implementation'
    COMMIT = 'commit'


class EnvironmentCfg:
    log_level: Optional[LogLevel] = None
    log_dir: Optional[str] = None
    build_dir: Optional[str] = None
    docker_registry: Optional[str] = "localhost:4000"
    tag_appendix: Optional[str] = None
    push_local_images: Optional[bool] = False

    def __str__(self):
        return (f"EnvironmentCfg: \n"
                f"    log_level={self.log_level}, \n"
                f"    log_dir={self.log_dir}, \n"
                f"    build_dir={self.build_dir}, \n"
                f"    docker_registry={self.docker_registry}, \n"
                f"    tag_appendix={self.tag_appendix}")


class SetupConfiguration:
    environment: Optional[EnvironmentCfg] = None
    near_rt_ric: Optional[NearRtRICCFG] = None
    core_5g: Optional[Core5GCfg] = None
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
