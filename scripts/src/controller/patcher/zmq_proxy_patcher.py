import os
from typing import Optional

import yaml
from jinja2 import Environment, FileSystemLoader

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.setup_configuration import SetupConfiguration
from model.ue_config import USIMMode, USIMAlgo


class ZMQProxyPatcher(SinglePatcherBase):

    def __init__(self, patch_file_path: str, setup_config: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_config, patcher_utils)

    def patch(self):
        pass

    def patch_config_file(self):
        pass

    def patch_docker_compose(self) -> Optional[dict]:
        FolderManager.create_patch_folders(self._patch_file_path)
        template_path = os.path.join(self._patch_file_path, "templates", "docker", "zmq-proxy")
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("docker-compose.ini.j2")
        rendered = template.render(
            image=f"{self._setup_cfg.environment.docker_registry}/zmq_proxy{self._patcher_utils.get_tag_or_empty_string(':')}",
            zmq_proxy_ip=self._setup_cfg.zmq_proxy.ip_addr,
            nr_of_ues=len(self._setup_cfg.ue.ues),
        )
        return yaml.safe_load(rendered)['services']

    def copy_config_files(self):
        pass
