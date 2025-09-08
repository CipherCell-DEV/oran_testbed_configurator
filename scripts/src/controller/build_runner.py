import logging
import os
import subprocess
from typing import List

from tqdm import tqdm

from scripts.src.model.setup_configuration import SetupConfiguration, BuildType, RICImplementation, CoreImplementation


class BuildRunner:
    """
    Class to handle the build process of RIC, 5G Core, gNB, and UE components.
    It supports both Docker-based and native builds.
    """

    def __init__(self, setup_configuration: SetupConfiguration):
        self.setup_cfg = setup_configuration

    def _create_log_dir(self):
        """Create log directory if it doesn't exist."""
        if self.setup_cfg.environment.log_dir:
            os.makedirs(self.setup_cfg.environment.log_dir, exist_ok=True)
            logging.info(f"Log directory created at {self.setup_cfg.environment.log_dir}")
        else:
            logging.warning("Log directory not specified in configuration.")

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
        self._create_log_dir()
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

    def build_ric(self):
        """
        Build the RIC component based on the specified implementation and build type.
        Returns: None
        """
        logging.info("Running RIC build process...")
        os.chdir(self.setup_cfg.environment.build_dir)

        if self.setup_cfg.near_rt_ric.type == RICImplementation.ORAN_SC_RIC:
            os.chdir("oran-sc-ric")
            if self.setup_cfg.environment.build_type == BuildType.DOCKER:
                self._build_docker_compose('oran-sc-ric', ["docker", "compose", "build"])
            else:
                logging.error("Building RIC natively currently not supported!")

    def build_5g_core(self):
        """
        Build the 5G Core Network component based on the specified implementation and build type.
        Returns:
        """
        logging.info("Running 5G Core Network build process...")
        os.chdir(self.setup_cfg.environment.build_dir)
        if self.setup_cfg.core_5g.implementation == CoreImplementation.SRS:
            os.chdir("srsRAN_Project/docker")
            if self.setup_cfg.environment.build_type == BuildType.DOCKER:
                self._build_docker_compose('5gc', ["docker", "compose", "build", '5gc'])
            else:
                logging.warning("Building 5GC natively... -> Currently not supported!")

    def build_gnb_ue(self):
        """
        Build the gNB and UE components based on the specified build types.
        Returns: None
        """
        logging.info("Running gNB and UE build process...")

        is_docker_ue = any(ue.build_type == BuildType.DOCKER for ue in self.setup_cfg.ue)

        if self.setup_cfg.gnb.build_type == BuildType.DOCKER or is_docker_ue:
            logging.info("Building gNB and UE using Docker...")
            os.chdir(self.setup_cfg.environment.build_dir)
            self._build_docker_compose('gnb_ue', ["docker", "compose", "build"])
        else:  # native build
            logging.error("Building gNB and UE natively... -> Currently not supported!")
