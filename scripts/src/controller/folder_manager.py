import logging
import os
from typing import List

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.setup_configuration import SetupConfiguration
from model.ue_config import UEImplementation


class FolderManager:

    @staticmethod
    def _create_path_helper(path_list: List[str]) -> str:
        """Create nested folders from a list of path segments."""
        current_path = ""
        for i in range(len(path_list)):
            current_path = os.path.join(current_path, path_list[i])
            if not os.path.exists(current_path):
                logging.info(f"Creating missing folder: {current_path}")
                os.makedirs(current_path)
        return current_path

    @staticmethod
    def create_patch_folders(path_file_path: str):
        FolderManager._create_path_helper([path_file_path, "patched", "docker"])
        FolderManager._create_path_helper([path_file_path, "patched", "config"])

    @staticmethod
    def add_config_folder(path_file_path: str, component_type: str, component_name: str) -> str:
        return FolderManager._create_path_helper([path_file_path, "patched", "config", component_type, component_name])

    @staticmethod
    def add_docker_folder(path_file_path: str, component_type: str, component_name: str) -> str:
        return FolderManager._create_path_helper([path_file_path, "patched", "docker", component_type, component_name])

    @staticmethod
    def create_folder(path: str, component_name: str):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logging.info(f"Created config folder for {component_name} at {path}")

    @staticmethod
    def create_project_config_folders(setup_cfg: SetupConfiguration):

        if setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS:
            srs_core_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_Project", "configs")
            FolderManager.create_folder(srs_core_path, "srsRAN_Project")

        if setup_cfg.gnb.implementation == GNBImplementation.SRS:
            srs_gnb_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_Project", "configs")
            FolderManager.create_folder(srs_gnb_path, "srsRAN_Project (gNB)")

        for ue in setup_cfg.ue.ues:
            if ue.implementation == UEImplementation.SRS_4G:
                srs_ue_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_4G", "configs")
                FolderManager.create_folder(srs_ue_path, "srsRAN_4G")

    @staticmethod
    def create_project_build_folders(setup_cfg: SetupConfiguration):
        oran_sc_ric_images = ["appmgr", "submgr", "e2term", "rtmgr_sim", "e2mgr", "ric_plt_frame_py"]
        for folder in oran_sc_ric_images:
            sc_ric_path = os.path.join(setup_cfg.environment.build_dir, "oran-sc-ric", "ric", "images", folder)
            FolderManager.create_folder(sc_ric_path, folder)

    @staticmethod
    def create_log_dir(setup_cfg: SetupConfiguration):
        """Create log directory if it doesn't exist."""
        if setup_cfg.environment.log_dir:
            os.makedirs(setup_cfg.environment.log_dir, exist_ok=True)
            logging.info(f"Log directory created at {setup_cfg.environment.log_dir}")
        else:
            logging.warning("Log directory not specified in configuration.")

    @staticmethod
    def create_native_build_folder(build_dir: str, project_folder: str):
        os.makedirs(os.path.join(build_dir, project_folder, 'build'), exist_ok=True)
