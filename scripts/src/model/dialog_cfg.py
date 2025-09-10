from dataclasses import dataclass
from typing import Optional

from model.utils_config import BuildType


@dataclass
class DialogConfig:
    build_core_net: Optional[bool] = True
    build_near_rt_ric: Optional[bool] = True
    build_gnb: Optional[bool] = True
    build_ue: Optional[bool] = True
    build_type: Optional[BuildType] = BuildType.DOCKER
