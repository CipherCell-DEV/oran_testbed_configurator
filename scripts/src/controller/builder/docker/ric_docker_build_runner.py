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
        os.chdir(self.setup_cfg.environment.build_dir)
        if self.setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            return self.docker_compose_build_helper('oran-sc-ric', ORAN_SC_RIC_CONTAINERS)
        return False
