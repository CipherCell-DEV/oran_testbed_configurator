import logging
import os

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.setup_configuration import SetupConfiguration
from model.ue_config import UEImplementation


class FolderManager():

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
    def create_project_config_folders(setup_cfg: SetupConfiguration):
        def create_folder(path: str, component_name: str):
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                logging.info(f"Created config folder for {component_name} at {path}")

        if setup_cfg.core_5g.implementation == CoreImplementation.SRS:
            srs_core_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_Project", "configs")
            create_folder(srs_core_path, "srsRAN_Project")

        if setup_cfg.gnb.type == GNBImplementation.SRS:
            srs_gnb_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_Project", "configs")
            create_folder(srs_gnb_path, "srsRAN_Project (gNB)")

        for ue in setup_cfg.ue:
            if ue.implementation == UEImplementation.SRS_4G:
                srs_ue_path = os.path.join(setup_cfg.environment.build_dir, "srsRAN_4G", "configs")
                create_folder(srs_ue_path, "srsRAN_4G")

    @staticmethod
    def create_log_dir(setup_cfg: SetupConfiguration):
        """Create log directory if it doesn't exist."""
        if setup_cfg.environment.log_dir:
            os.makedirs(setup_cfg.environment.log_dir, exist_ok=True)
            logging.info(f"Log directory created at {setup_cfg.environment.log_dir}")
        else:
            logging.warning("Log directory not specified in configuration.")
