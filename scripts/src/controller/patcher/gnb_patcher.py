import logging
import os
from typing import Optional

import yaml

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.setup_configuration import SetupConfiguration


class GnbPatcher(SinglePatcherBase):
    def __init__(self, patch_file_path: str, setup_config: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_config, patcher_utils)
        self._patch_file_path = patch_file_path
        self._setup_cfg = setup_config
        self._patcher_utils = patcher_utils

    def patch(self):
        pass

    def patch_config_file(self):
        patch_file_path = os.path.join(self._patch_file_path, "templates", "config", "gnb",
                                       str(self._setup_cfg.gnb.implementation.value), "gnb_zmq.yaml")
        new_file_path = os.path.join(self._patch_file_path, "patched", "config", "gnb_zmq.yaml")

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

                patch_content['cu_cp']['amf']['addr'] = f"{self._setup_cfg.core_5g.ip}"

                patch_content['cu_cp']['amf']['bind_addr'] = f"{self._setup_cfg.gnb.ip_config.cu_cp}"

                patch_content['ru_sdr']['device_args'] = (
                    f"tx_port=tcp://0.0.0.0:2000,"
                    f"rx_port=tcp://{self._setup_cfg.ue[0].ip}:2001,"  # TODO Allow multiple UEs
                    f"base_srate={self._setup_cfg.gnb.srate}"
                )

                patch_content['ru_sdr']['srate'] = float(self._setup_cfg.gnb.srate) / 1e6
                patch_content['ru_sdr']['tx_gain'] = self._setup_cfg.gnb.tx_gain
                patch_content['ru_sdr']['rx_gain'] = self._setup_cfg.gnb.rx_gain

                patch_content['e2']['bind_addr'] = f"{self._setup_cfg.gnb.ip_config.e2}"
                patch_content['e2']['addr'] = f"{self._setup_cfg.near_rt_ric.ip_config.e2term_ip}"

                with open(new_file_path, "w") as new_file:
                    yaml.safe_dump(
                        patch_content,
                        new_file,
                        default_flow_style=False,
                        sort_keys=False
                    )

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def patch_docker_compose(self) -> Optional[dict]:
        FolderManager.create_patch_folders(self._patch_file_path)

        patch_file_path = os.path.join(self._patch_file_path, "templates", "docker", "gnb",
                                       str(self._setup_cfg.gnb.implementation.value), "docker_compose.yml")
        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)
                patch_content["services"]["gnb"].update(
                    {"image": self._patcher_utils.replace_tag_and_image(patch_content["services"]["gnb"]["image"])})
                return patch_content
        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def copy_config_files(self):
        src_dirs = [[self._patch_file_path, "patched", "config"],
                    [self._patch_file_path, "templates", "docker", "gnb", self._setup_cfg.gnb.implementation.value]]
        dest_dirs = [[self._setup_cfg.environment.build_dir, "srsRAN_Project", "configs"],
                     [self._setup_cfg.environment.build_dir, "srsRAN_Project", ]]
        src_filenames = ["gnb_zmq.yaml", "dockerfile_gnb"]
        dest_filenames = ["gnb_zmq.yaml", "Dockerfile"]

        super().copy_helper(src_dirs, src_filenames, dest_dirs, dest_filenames)
