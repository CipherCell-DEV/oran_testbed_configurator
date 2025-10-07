import logging
import os

from controller.builder.docker.docker_builder_base import DockerBuilderBase
from model.setup_configuration import SetupConfiguration
from model.ue_config import UECfg


class UEDockerBuildRunner(DockerBuilderBase):
    def __init__(self, setup_cfg: SetupConfiguration, ue: UECfg):
        super().__init__(setup_cfg)
        self._ue = ue

    def build(self) -> bool:
        logging.info("Building UE using Docker...")
        os.chdir(self.setup_cfg.environment.build_dir)
        return self.docker_compose_build_helper('ue', ["docker", "compose", "build", self._ue.name])
