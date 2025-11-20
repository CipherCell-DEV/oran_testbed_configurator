import os

from controller.builder.docker.docker_builder_base import DockerBuilderBase
from model.ric_config import RICImplementation

ORAN_SC_RIC_CONTAINERS = ["docker", "compose", "build",
                          "dbaas", "rtmgr_sim", "submgr", "e2term", "appmgr",
                          "e2mgr", "python_xapp_runner"]


class NearRTRICDockerBuildRunner(DockerBuilderBase):
    def __init__(self, setup_cfg):
        super().__init__(setup_cfg)

    def build(self) -> bool:
        result = False
        curr_dir = os.getcwd()
        os.chdir(self.setup_cfg.environment.build_dir)
        if self.setup_cfg.get_used_ric().implementation == RICImplementation.ORAN_SC_RIC:
            result = self.docker_compose_build_helper('oran-sc-ric', ORAN_SC_RIC_CONTAINERS)
        if self.setup_cfg.get_used_ric().implementation == RICImplementation.FLEX_RIC:
            result = self.docker_compose_build_helper('flexric', ["docker", "compose", "build", "flexric"])
        os.chdir(curr_dir)
        return result
