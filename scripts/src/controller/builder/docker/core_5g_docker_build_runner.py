import logging
import os

from controller.builder.docker.docker_builder_base import DockerBuilderBase
from model.core_config import CoreImplementation


class Core5GDockerBuildRunner(DockerBuilderBase):
    def __init__(self, setup_cfg):
        super().__init__(setup_cfg)

    def build(self) -> bool:
        curr_dir = os.getcwd()
        os.chdir(self.setup_cfg.environment.build_dir)  # TODO is this necessary?
        if self.setup_cfg.environment.core_implementation == CoreImplementation.OPEN5GS_SRS:
            result = self.docker_compose_build_helper('5gc', ["docker", "compose", "build", '5gc'])
            os.chdir(curr_dir)
            return result
        if self.setup_cfg.environment.core_implementation == CoreImplementation.OPEN5GS:
            result = self.docker_compose_build_helper('5gc', ["docker", "compose", "build", '5gc', 'mongodb'])
            os.chdir(curr_dir)
            return result
        else:
            logging.error(
                "The selected 5G Core implementation is not supported. Currently, only SRS 5G Core is supported.")
        os.chdir(curr_dir)
        return False
