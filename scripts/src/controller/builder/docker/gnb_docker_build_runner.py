import logging
import os

from controller.builder.docker.docker_builder_base import DockerBuilderBase
from model.setup_configuration import SetupConfiguration


class GNBDockerBuildRunner(DockerBuilderBase):
    def __init__(self, setup_cfg: SetupConfiguration):
        super().__init__(setup_cfg)

    def build(self) -> bool:
        logging.info("Building gNB using Docker...")
        curr_dir = os.getcwd()
        os.chdir(self.setup_cfg.environment.build_dir)
        result = self.docker_compose_build_helper('gnb', ["docker", "compose", "build", "gnb"])
        os.chdir(curr_dir)
        return result
