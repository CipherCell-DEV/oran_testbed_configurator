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
        # TODO solve multiple UEs with different implementations
        config_paths = [[self._patch_file_path, "patched", "config", "ue",
                         str(self._setup_cfg.ue.ues[0].implementation.value)] for _ in self._setup_cfg.ue.ues]

        template_paths = [
            [self._patch_file_path, "templates", "docker", "ue", str(self._setup_cfg.ue.ues[0].implementation.value)],
            [self._patch_file_path, "templates", "config", "ue", str(self._setup_cfg.ue.ues[0].implementation.value)]
        ]
        paths_src = config_paths + template_paths

        # Destination Paths
        build_dir = self._setup_cfg.environment.build_dir
        config_dst = [[build_dir, "srsRAN_4G", "configs"] for _ in self._setup_cfg.ue.ues]
        template_dst = [
            [build_dir, "srsRAN_4G"],
            [build_dir, "srsRAN_4G"]
        ]
        paths_dst = config_dst + template_dst

        config_files = [f"{ue.name}_zmq.conf" for ue in self._setup_cfg.ue.ues]
        file_name = config_files + ["Dockerfile", "ue_entrypoint.sh"]
        super().copy_helper(paths_src, file_name, paths_dst, file_name)

    def _get_usim_mode(self):
        if self._setup_cfg.ue.ues[0].usim.mode == USIMMode.HARD:
            return "hard"
        elif self._setup_cfg.ue.ues[0].usim.mode == USIMMode.SOFT:
            return "soft"

    def _get_usim_algorithm(self):
        if self._setup_cfg.ue.ues[0].usim.algo == USIMAlgo.XOR:
            return "xor"  # NOT TESTED
        elif self._setup_cfg.ue.ues[0].usim.algo == USIMAlgo.COMP:
            return "comp"  # NOT TESTED
        elif self._setup_cfg.ue.ues[0].usim.algo == USIMAlgo.MILENAGE:
            return "milenage"
