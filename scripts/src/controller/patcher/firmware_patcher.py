import logging
import os
from enum import Enum
from typing import Dict, Any, List, Optional

import yaml

from controller.folder_manager import FolderManager
from controller.patcher.core_5g_patcher import Core5GPatcher
from controller.patcher.generic_patcher import GenericPatcher
from controller.patcher.gnb_patcher import GnbPatcher
from controller.patcher.near_rt_ric_patcher import NearRTRICPatcher
from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from controller.patcher.ue_patcher import UEPatcher
from model.core_config import CoreImplementation
from model.setup_configuration import SetupConfiguration


class PatchListOrder(Enum):
    """Enum to define the order of patchers in the patcher list.
    """
    RIC = 0
    CORE_5G = 1
    GNB = 2
    UE = 3
    GENERIC = 4


class FirmwarePatcher:
    """ Class to patch firmware configuration files based on the provided setup configuration.
    It supports patching for different components like RIC, 5G Core, gNB, and UE.
    """

    def __init__(self, setup_configuration: SetupConfiguration, patch_file_path: str):
        self._setup_cfg = setup_configuration
        self._patch_file_path = patch_file_path
        self._images_to_push = list()
        self._patcher_utils = PatcherUtils(self._setup_cfg)

        self._patcher_list: List[Optional[SinglePatcherBase]] = [None] * len(PatchListOrder)
        self.initialize_patchers()

    def initialize_patchers(self):
        """
        Initialize patchers for different components and store them in the patcher list.
        """
        params = [self._patch_file_path, self._setup_cfg, self._patcher_utils]

        self._patcher_list[PatchListOrder.RIC.value] = NearRTRICPatcher(*params)
        self._patcher_list[PatchListOrder.CORE_5G.value] = Core5GPatcher(*params)
        self._patcher_list[PatchListOrder.GNB.value] = GnbPatcher(*params)
        self._patcher_list[PatchListOrder.UE.value] = UEPatcher(*params)
        self._patcher_list[PatchListOrder.GENERIC.value] = GenericPatcher(*params)

    def get_images_to_push(self):
        return self._images_to_push

    def patch_single_docker_compose(self) -> bool:
        """
        Combine RIC, 5G Core, and UE/gNB docker-compose fragments
        into a single docker-compose file.

        Returns:
            bool: True if the combined file was successfully created,
                  False otherwise.
        """
        try:
            ric_config: Dict[str, Any] = self._patcher_list[PatchListOrder.RIC.value].patch()
            core_config: Dict[str, Any] = self._patcher_list[PatchListOrder.CORE_5G.value].patch()
            ue_gnb_config = self._patcher_list[PatchListOrder.GNB.value].patch_docker_compose()
            ue_gnb_config['services'].update(self._patcher_list[PatchListOrder.UE.value].patch_docker_compose())

            self._patcher_list[PatchListOrder.UE.value].patch_config_file()
            self._patcher_list[PatchListOrder.GNB.value].patch_config_file()

            self.patch_single_env_file()

            single_config: Dict[str, Any] = {
                "services": dict(ric_config.get("services", {})),
                "networks": dict(ric_config.get("networks", {}))
            }

            if self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS_SRS:
                if "volumes" in core_config:
                    single_config["volumes"] = dict(core_config["volumes"])

            elif self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS:
                logging.warning("Currently not supported")
            else:
                logging.error(
                    "Currently only SRS RAN is supported for 5G Core implementation."
                )
                return False

            single_config["networks"].update(core_config.get("networks", {}))
            single_config["services"].update(core_config.get("services", {}))
            single_config["services"].update(ue_gnb_config.get("services", {}))

            if "networks" in ue_gnb_config and "internal_net" in ue_gnb_config["networks"]:
                single_config["networks"]["internal_net"] = ue_gnb_config["networks"]["internal_net"]

            combined_file_path = os.path.join(
                self._patch_file_path, "patched", "docker", "docker_combined.yml"
            )

            for service in single_config["services"]:
                if "image" in single_config["services"][service]:
                    if self._setup_cfg.environment.docker_registry in single_config["services"][service]["image"]:
                        self._images_to_push.append(service)

            with open(combined_file_path, "w", encoding="utf-8") as new_file:
                yaml.safe_dump(
                    single_config,
                    new_file,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2
                )

            logging.info(f"Combined docker-compose written to {combined_file_path}")
            return True

        except Exception as e:
            logging.exception(f"Failed to patch single docker-compose: {e}")
            return False

    def patch_single_env_file(self):
        """Merges and patches environment files for all components.

        Combines environment variables from all patchers and writes
        a unified `.env` file in the patched output directory.
        """
        FolderManager.create_patch_folders(self._patch_file_path)

        env_dict = dict()
        for i, patcher in enumerate(self._patcher_list):
            env_dict = patcher.patch_env_file(env_dict)

        PatcherUtils.patch_env_file(self._patch_file_path, env_dict)

    def copy_files_to_location(self):
        """Copies all patched configuration files to the appropriate build directories.
        """
        logging.info("Copying patched files to build directory...")
        FolderManager.create_project_config_folders(self._setup_cfg)
        FolderManager.create_project_build_folders(self._setup_cfg)

        for patcher in self._patcher_list:
            patcher.copy_config_files()
