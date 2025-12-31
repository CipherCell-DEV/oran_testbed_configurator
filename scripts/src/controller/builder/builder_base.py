from abc import ABCMeta
from typing import Optional

from api.api_state import LogQueue
from controller.builder.utils import BuildUtils
from model.setup_configuration import SetupConfiguration


class BuilderBase(metaclass=ABCMeta):
    def __init__(self, setup_cfg: SetupConfiguration):
        self.setup_cfg: SetupConfiguration = setup_cfg
        self.utils = BuildUtils(setup_cfg)

    def build(self,  log_buffer: Optional[LogQueue] = None) -> bool:
        raise NotImplementedError("Subclasses should implement this method.")
