import logging
import os
import subprocess
from typing import List

from tqdm import tqdm

from controller.folder_manager import FolderManager
from model.setup_configuration import SetupConfiguration

from model.core_config import CoreImplementation
from model.ric_config import RICImplementation
from model.utils_config import BuildType


class BuildRunner:
    """
    Class to handle the build process of RIC, 5G Core, gNB, and UE components.
    It supports both Docker-based and native builds.
    """

    def __init__(self, setup_configuration: SetupConfiguration):
        self.setup_cfg = setup_configuration

    @staticmethod
    def _check_docker_compose_daemon_is_running() -> bool:
        try:
            subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except subprocess.CalledProcessError:
            logging.error("Docker does not appear to be running. Please start Docker before building components.")
            return False

    def _build_docker_compose(self, component_name: str, command: List[str]):
        """
        /**
         * @brief Build a component with Docker Compose and log the output.
         *
         * Executes the given command, writes logs to <log_dir>/<component>.log,
         * and shows a progress bar. Raises CalledProcessError on failure.
         *
         * @param component_name Component name (used for logging).
         * @param command Docker Compose command as a list of strings.
         */
        """
        if not BuildRunner._check_docker_compose_daemon_is_running():
            logging.error("Quit current build")
            return False

        FolderManager.create_log_dir(self.setup_cfg)
        log_path = os.path.join(self.setup_cfg.environment.log_dir, f"{component_name}.log")

        logging.info(f"Building {component_name} using Docker...")
        with open(log_path, "w") as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            with tqdm(desc=f"Building {component_name}", unit="line") as pbar:
                for line in process.stdout:
                    log_file.write(line)
                    pbar.update(1)

            process.wait()
            if process.returncode != 0:
                logging.error(f"{component_name} build failed. See %s for details.", log_path)
                raise subprocess.CalledProcessError(process.returncode, process.args)

            logging.info("RIC Docker build completed successfully ✅ (log: %s)",
                         log_path)
            print()
            return True

    def build_ric(self) -> bool:
        """
        Build the RIC component based on the specified implementation and build type.
        Returns: None
        """
        logging.info("Running RIC build process...")
        os.chdir(self.setup_cfg.environment.build_dir)

        if self.setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            if self.setup_cfg.near_rt_ric.build_type == BuildType.DOCKER:
                return self._build_docker_compose('oran-sc-ric', ["docker", "compose", "build",
                                                                  "dbaas", "rtmgr_sim", "submgr", "e2term", "appmgr",
                                                                  "e2mgr", "python_xapp_runner"])
            else:
                logging.error("Building RIC natively currently not supported!")
        return False

    def build_5g_core(self) -> bool:
        """
        Build the 5G Core Network component based on the specified implementation and build type.
        Returns:
        """
        logging.info("Running 5G Core Network build process...")
        os.chdir(self.setup_cfg.environment.build_dir)
        if self.setup_cfg.core_5g.implementation == CoreImplementation.SRS:
            if self.setup_cfg.core_5g.build_type == BuildType.DOCKER:
                return self._build_docker_compose('5gc', ["docker", "compose", "build", '5gc'])
            else:
                logging.error("Building 5GC natively... -> Currently not supported!")
        else:
            logging.error(
                "The selected 5G Core implementation is not supported. Currently, only SRS 5G Core is supported.")
        return False

    def build_gnb(self) -> bool:
        """
        Build the gNB and UE components based on the specified build types.
        Returns: None
        """
        logging.info("Running gNB build process...")

        if self.setup_cfg.gnb.build_type == BuildType.DOCKER:
            logging.info("Building gNB using Docker...")
            os.chdir(self.setup_cfg.environment.build_dir)
            return self._build_docker_compose('gnb', ["docker", "compose", "build", "gnb"])
        else:  # native build
            logging.error("Building gNB natively... -> Currently not supported!")
            return False

    def build_ues(self) -> bool:
        """
        Build the gNB and UE components based on the specified build types.
        Returns: None
        """
        logging.info("Running UE build process...")
        os.chdir(self.setup_cfg.environment.build_dir)
        for ue in self.setup_cfg.ue:
            if ue.build_type == BuildType.DOCKER:
                logging.info(f"Building UE ({ue.name}) using Docker...")
                ue_ret = self._build_docker_compose('ue', ["docker", "compose", "build", ue.name])
                if not ue_ret:
                    return False
            elif ue.build_type == BuildType.NATIVE:
                logging.error(f"Building UE {ue.name} natively... -> Currently not supported!")
                return False
        return True

    def push_images(self, images_to_push: list[str]) -> bool:
        if not self.setup_cfg.environment.push_local_images:
            return True
        for image in images_to_push:
            logging.info(f"Pushing {image}")
            process = subprocess.Popen(
                f"docker compose push {image}".split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=self.setup_cfg.environment.build_dir
            )

            if process.wait() != 0:
                logging.error(f"Failed to push {image}")
                return False
        return True
