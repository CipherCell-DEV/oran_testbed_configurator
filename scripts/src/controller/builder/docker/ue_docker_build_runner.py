import logging
import os

from controller.builder.docker.docker_builder_base import DockerBuilderBase
from model.setup_configuration import SetupConfiguration
from model.ue_config import UEInstCfg


class UEDockerBuildRunner(DockerBuilderBase):
    def __init__(self, setup_cfg: SetupConfiguration, ue: UEInstCfg):
        super().__init__(setup_cfg)
        self._ue = ue

    def build(self) -> bool:
        logging.info("Building UE using Docker...")
        curr_dir = os.getcwd()
        os.chdir(self.setup_cfg.environment.build_dir)
        result = self.docker_compose_build_helper('ue', ["docker", "compose", "build", self._ue.name])
        os.chdir(curr_dir)
        return result