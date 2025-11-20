import os
from typing import Optional

import yaml
from jinja2 import Environment, FileSystemLoader

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.setup_configuration import SetupConfiguration
from model.ue_config import USIMMode, USIMAlgo


class UEPatcher(SinglePatcherBase):

    def __init__(self, patch_file_path: str, setup_config: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_config, patcher_utils)
        self._patch_file_path = patch_file_path
        self._setup_cfg = setup_config
        self._patcher_utils = patcher_utils

    def patch(self):
        pass

    def patch_config_file(self):
        # TODO support multiple UE implementations
        template_path = os.path.join(self._patch_file_path, "templates", "config", "ue",
                                     str(self._setup_cfg.ue.ues[0].implementation.value))
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("ue_config.ini.j2")

        rendered_configs = []
        for ue in self._setup_cfg.ue.ues:
            rendered = template.render(
                ue=ue,
                gnb_ip=self._setup_cfg.get_used_gnb().ip_config.ru_sdr,
                usim_mode=self._get_usim_mode(),
                usim_algo=self._get_usim_algorithm()
            )
            # TODO support multiple UEs
            out_path = os.path.join(FolderManager.add_config_folder(self._patch_file_path, "ue",
                                    str(self._setup_cfg.ue.ues[0].implementation.value)),
                                    f"{ue.name}_zmq.conf")

            with open(out_path, "w") as new_file:
                new_file.write(rendered)

    def patch_docker_compose(self) -> Optional[dict]:
        FolderManager.create_patch_folders(self._patch_file_path)
        for i, ue in enumerate(self._setup_cfg.ue.ues):
            template_path = os.path.join(self._patch_file_path, "templates", "docker", "ue",
                                         str(ue.implementation.value))
            env = Environment(loader=FileSystemLoader(template_path))
            template = env.get_template("docker_compose.ini.j2")
            rendered = template.render(
                image=f"{self._setup_cfg.environment.docker_registry}/ue{self._patcher_utils.get_tag_or_empty_string(':')}",
                ue=ue
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
