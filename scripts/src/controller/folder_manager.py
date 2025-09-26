import logging
import os

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.setup_configuration import SetupConfiguration
from model.ue_config import UEImplementation


class FolderManager:

    @staticmethod
    def create_patch_folders(path_file_path: str):
        patched_folder = os.path.join(path_file_path, "patched")
        docker_folder = os.path.join(path_file_path, "patched", "docker")
        config_folder = os.path.join(path_file_path, "patched", "config")

        for folder in [patched_folder, docker_folder, config_folder]:
            if not os.path.exists(folder):
                logging.info(f"Implement non existing folder {folder}")
                os.makedirs(folder)

    @staticmethod
    def create_folder(path: str, component_name: str):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logging.info(f"Created config folder for {component_name} at {path}")

    @staticmethod
    def create_project_config_folders(setup_cfg: SetupConfiguration):

        if setup_cfg.core_5g.implementation == CoreImplementation.SRS:
            srs_core_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_Project", "configs")
            FolderManager.create_folder(srs_core_path, "srsRAN_Project")

        if setup_cfg.gnb.implementation == GNBImplementation.SRS:
            srs_gnb_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_Project", "configs")
            FolderManager.create_folder(srs_gnb_path, "srsRAN_Project (gNB)")

        for ue in setup_cfg.ue:
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
