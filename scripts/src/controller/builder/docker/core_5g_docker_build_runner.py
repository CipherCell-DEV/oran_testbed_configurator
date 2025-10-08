import logging
import os

from controller.builder.docker.docker_builder_base import DockerBuilderBase
from model.core_config import CoreImplementation


class Core5GDockerBuildRunner(DockerBuilderBase):
    def __init__(self, setup_cfg):
        super().__init__(setup_cfg)

    def build(self) -> bool:
        os.chdir(self.setup_cfg.environment.build_dir)  # TODO is this necessary?
        if self.setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS_SRS:
            return self.docker_compose_build_helper('5gc', ["docker", "compose", "build", '5gc'])
        if self.setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS:
            return self.docker_compose_build_helper('5gc', ["docker", "compose", "build", '5gc', 'mongodb'])
        else:
            logging.error(
                "The selected 5G Core implementation is not supported. Currently, only SRS 5G Core is supported.")
        return False
