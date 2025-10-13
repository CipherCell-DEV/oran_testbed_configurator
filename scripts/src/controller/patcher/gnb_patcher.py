import logging
import os
import re
from typing import Optional

import yaml

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.setup_configuration import SetupConfiguration
from model.utils_config import BuildType

from jinja2 import Environment, FileSystemLoader


class GnbPatcher(SinglePatcherBase):
    def __init__(self, patch_file_path: str,
                 setup_config: SetupConfiguration,
                 patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_config, patcher_utils)
        self._patch_file_path = patch_file_path
        self._setup_cfg = setup_config
        self._patcher_utils = patcher_utils

    def patch(self):
        pass

    def patch_config_file(self):
        template_path = os.path.join(self._patch_file_path, "templates", "config", "gnb",
                                     str(self._setup_cfg.gnb.implementation.value))
        patched_file = os.path.join(FolderManager.
                                    add_config_folder(self._patch_file_path, "gnb",
                                                      str(self._setup_cfg.gnb.implementation.value)), "gnb_zmq.yaml")

        env = Environment(loader=FileSystemLoader(template_path))
        config_file_name = "gnb_zmq.ini.j2"
        template = env.get_template(config_file_name)
        rendered = template.render(
            core5g=self._setup_cfg.core_5g,
            ric=self._setup_cfg.near_rt_ric,
            gnb=self._setup_cfg.gnb,
            ue=self._setup_cfg.ue.ues[0],
            pcap=self._parse_pcap_dict(template_path, config_file_name)
        )

        with open(patched_file, "w") as new_file:
            new_file.write(rendered)

    def _parse_pcap_dict(self, template_path: str, config_file_name: str) -> dict:
        pcap_dict = dict()
        with open(os.path.join(template_path, config_file_name), "r") as template_file:
            lines = template_file.read()
            # replace placeholders to enable yaml parsing.
            text = re.sub(r"{{\s*[\S]+\s*}}", "dummy", lines)
            try:
                yaml_ret = yaml.safe_load(text)
                for entry in yaml_ret['pcap'].keys():
                    if entry.__str__().endswith("_filename"):
                        if self._setup_cfg.gnb.build_type == BuildType.DOCKER:
                            # write files to docker volume
                            log_file_path = os.path.join("/logs", "gnb")
                        else:
                            # write files locally
                            log_file_path = os.path.join(self._setup_cfg.environment.log_dir, "gnb")

                        component_name = entry.split("_filename")[0]
                        log_file_name = component_name + ".pcap"
                        log_file_path = os.path.join(log_file_path, log_file_name)
                        pcap_dict[component_name] = {
                            'filename': log_file_path
                        }
            except yaml.YAMLError as e:
                logging.error(f"Failed to parse YAML patch file: {e}")
                raise
        return pcap_dict

    def patch_docker_compose(self) -> Optional[dict]:
        FolderManager.create_patch_folders(self._patch_file_path)

        template_path = os.path.join(self._patch_file_path, "templates", "docker", "gnb",
                                     str(self._setup_cfg.gnb.implementation.value))
        env = Environment(loader=FileSystemLoader(template_path))
        template = env.get_template("docker_compose.ini.j2")
        rendered = template.render(
            gnb=self._setup_cfg.gnb,
            image=self._patcher_utils.replace_tag_and_image("localhost:4000/gnb:selftag"),
            log_file_path=os.path.join(self._setup_cfg.environment.log_dir, "gnb")
        )
        return yaml.safe_load(rendered)

    def copy_config_files(self):
        src_dirs = [[self._patch_file_path, "patched", "config", "gnb", self._setup_cfg.gnb.implementation.value],
                    [self._patch_file_path, "templates", "docker", "gnb", self._setup_cfg.gnb.implementation.value]]
        dest_dirs = [[self._setup_cfg.environment.build_dir, "srsRAN_Project", "configs"],
                     [self._setup_cfg.environment.build_dir, "srsRAN_Project", ]]
        file_names = ["gnb_zmq.yaml", "Dockerfile"]

        super().copy_helper(src_dirs, file_names, dest_dirs, file_names)
