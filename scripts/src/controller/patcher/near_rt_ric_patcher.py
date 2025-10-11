import logging
import os
from typing import Optional

import yaml

from controller.folder_manager import FolderManager
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.ric_config import RICImplementation, ORAN_SC_RIC_SERVICE_IP_MAP
from model.setup_configuration import SetupConfiguration
from model.utils_config import BuildType


class NearRTRICPatcher(SinglePatcherBase):

    def __init__(self, patch_file_path: str, setup_config: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_config, patcher_utils)
        self._patch_file_path = patch_file_path
        self._setup_cfg = setup_config
        self._patcher_utils = patcher_utils

    def patch(self):
        logging.info("Patching RIC firmware...")
        if os.path.exists(self._patch_file_path):
            if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
                return self._patch_oran_sc()
        else:
            raise FileNotFoundError(f"Patch file not found: {self._patch_file_path}")

    def patch_config_file(self):
        pass

    def patch_docker_compose(self) -> Optional[dict]:
        FolderManager.create_patch_folders(self._patch_file_path)
        """ Patch the ORAN SC RIC docker-compose.yml file with custom IP addresses and subnet. """
        patch_file_path = os.path.join(self._patch_file_path, "templates", "docker", "ric",
                                       str(self._setup_cfg.near_rt_ric.implementation.value), "oran_sc_docker.yml")

        try:
            with open(patch_file_path, "r") as patch_file:
                patch_content = yaml.safe_load(patch_file)

            logging.info("Patching ORAN SC RIC docker-compose.yml with custom IP addresses...")

            for service in patch_content["services"]:
                if "image" in patch_content["services"][service]:
                    patch_content["services"][service]["image"] = self._patcher_utils.replace_tag_and_image(
                        patch_content["services"][service]["image"])

            for service, (env_var, ip_attr) in ORAN_SC_RIC_SERVICE_IP_MAP.items():
                ip_value = getattr(self._setup_cfg.near_rt_ric.ip_config, ip_attr)
                patch_content["services"][service]["networks"]["ric_network"]["ipv4_address"] = (
                    f"${{{env_var}:-{ip_value}}}"
                )

            subnet_value = self._setup_cfg.near_rt_ric.ip_config.subnet
            patch_content["networks"]["ric_network"]["ipam"]["config"][0]["subnet"] = (
                f"{subnet_value}"
            )

            return patch_content

        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML patch file: {e}")
            raise

    def copy_config_files(self):
        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            docker_files = ["dockerfile_appmgr", "dockerfile_submgr", "dockerfile_e2term", "dockerfile_rtmgr_sim",
                            "dockerfile_e2mgr", "dockerfile_ric-plt-xapp-frame-py"]
            dst_file_paths = [
                [self._setup_cfg.environment.build_dir, "oran-sc-ric", "ric", "images", file.replace("dockerfile_", "")]
                for
                file in docker_files]

            super().copy_helper(
                [[self._patch_file_path, "templates", "docker", "ric",
                  str(self._setup_cfg.near_rt_ric.implementation.value)]
                 for _ in docker_files], docker_files,
                dst_file_paths, ["Dockerfile" for _ in docker_files])
        else:
            logging.error(f"{str(self._setup_cfg.near_rt_ric.implementation.value)} is not implemented yet.")
            exit(1)

    def _patch_oran_sc(self) -> dict:
        if self._setup_cfg.near_rt_ric.build_type == BuildType.DOCKER:
            return self.patch_docker_compose()
        else:
            logging.error("Native build patching for ORAN SC RIC is not implemented yet.")
            exit(1)

    def patch_env_file(self, env_dict: dict) -> dict:

        patch_file_path = os.path.join(self._patch_file_path, "templates", "config", "ric",
                                       str(self._setup_cfg.near_rt_ric.implementation.value), "oran_sc_ric_env")
        env_dict_oran_sc_ric = PatcherUtils.load_env_file_str_helper(patch_file_path)

        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            env_dict_oran_sc_ric['SC_RIC_VERSION'] = f'{self._setup_cfg.near_rt_ric.release}-release'
            env_dict_oran_sc_ric['SYSTEM_NAME'] = f'oran_sc_ric'

            env_dict_oran_sc_ric['RIC_SUBNET'] = f'{self._setup_cfg.near_rt_ric.ip_config.subnet}'
            env_dict_oran_sc_ric['E2TERM_IP'] = f'{self._setup_cfg.near_rt_ric.ip_config.e2term_ip}'
            env_dict_oran_sc_ric['E2MGR_IP'] = f'{self._setup_cfg.near_rt_ric.ip_config.e2mgr_ip}'
            env_dict_oran_sc_ric['DBAAS_IP'] = f'{self._setup_cfg.near_rt_ric.ip_config.dbaas_ip}'
            env_dict_oran_sc_ric['SUBMGR_IP'] = f'{self._setup_cfg.near_rt_ric.ip_config.submgr_ip}'
            env_dict_oran_sc_ric['APPMGR_IP'] = f'{self._setup_cfg.near_rt_ric.ip_config.appmgr_ip}'
            env_dict_oran_sc_ric['RTMGR_SIM_IP'] = f'{self._setup_cfg.near_rt_ric.ip_config.rtmgr_sim_ip}'
            env_dict_oran_sc_ric['XAPP_PY_RUNNER_IP'] = f'{self._setup_cfg.near_rt_ric.ip_config.xapp_runner_ip}'
        return env_dict | env_dict_oran_sc_ric
