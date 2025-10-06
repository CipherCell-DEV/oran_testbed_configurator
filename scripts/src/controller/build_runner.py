import logging
import os
import subprocess
from typing import List, Tuple

from tqdm import tqdm

from controller.folder_manager import FolderManager
from controller.utils import check_docker_compose_daemon_is_running, get_operating_system, OperatingSystem
from model.gnb_config import GNBImplementation, SRSRAN_GNB_DEPENDENCIES_LINUX
from model.setup_configuration import SetupConfiguration

from model.core_config import CoreImplementation
from model.ric_config import RICImplementation
from model.ue_config import UECfg, UEImplementation, SRSRAN_4G_UE_DEPENDENCIES_LINUX
from model.utils_config import BuildType


class BuildRunner:
    """
    Class to handle the build process of RIC, 5G Core, gNB, and UE components.
    It supports both Docker-based and native builds.
    """

    def __init__(self, setup_configuration: SetupConfiguration):
        self.setup_cfg = setup_configuration

    def _setup_logging(self, component_name: str) -> str:
        FolderManager.create_log_dir(self.setup_cfg)
        return os.path.join(self.setup_cfg.environment.log_dir, f"{component_name}.log")

    @staticmethod
    def _command_helper(working_dir: str, component_name: str, command: List[str], log_file, log_path: str):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=working_dir
        )

        with tqdm(desc=f"Building {component_name}", unit="line") as pbar:
            for line in process.stdout:
                log_file.write(line)
                pbar.update(1)

        process.wait()
        if process.returncode != 0:
            logging.error(f"{component_name} build failed. See %s for details.", log_path)
            raise subprocess.CalledProcessError(process.returncode, process.args)
        return True

    def _build_native(self, working_dir: List[str], component_name: str, command_list: List[List[str]]):
        log_path = self._setup_logging(component_name)
        full_working_dir = str(os.path.join(*working_dir))
        with open(log_path, "w") as log_file:
            for command in command_list:
                if not BuildRunner._command_helper(full_working_dir, component_name, command, log_file, log_path):
                    logging.error(f"{component_name} native build failed. See %s for details.", log_path)
                    return False
            return True

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
        if not check_docker_compose_daemon_is_running():
            logging.error("Quit current build")
            return False

        log_path = self._setup_logging(component_name)

        logging.info(f"Building {component_name} using Docker...")
        with open(log_path, "w") as log_file:
            if BuildRunner._command_helper(self.setup_cfg.environment.build_dir, component_name, command,
                                           log_file, log_path):
                logging.info("RIC Docker build completed successfully ✅ (log: %s)",
                             log_path)
                print()  # Add empty line to indicate that build is done!
                return True
            else:
                return False

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
        if self.setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS_SRS:
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
            logging.info(f"Building gNB native...")

            build_commands, working_dir, dependencies = self.get_gnb_impl_dependent_config()
            if not build_commands:
                return False

            if not self.install_dependencies(dependencies):
                return False

            return self._build_native(working_dir, "gnb", build_commands)

    def get_gnb_impl_dependent_config(self) -> Tuple[List[List[str]], List[str], List[str]]:
        if self.setup_cfg.gnb.implementation == GNBImplementation.SRS:
            FolderManager.create_native_build_folder(self.setup_cfg.environment.build_dir, "srsRAN_Project")
            return [
                ['cmake', '-DENABLE_UHD=OFF', '-DENABLE_ARMPL=OFF', '-DENABLE_EXPORT=ON', '-DENABLE_ZEROMQ=ON', '..'],
                ['make', '-j', str(os.cpu_count())]
            ], [self.setup_cfg.environment.build_dir, 'srsRAN_Project', "build"], SRSRAN_GNB_DEPENDENCIES_LINUX
        else:
            logging.error("The selected gNB implementation is not supported. Currently, only srsGNB is supported.")
            return [], [], []

    def get_ue_impl_specific_config(self, ue: UECfg) -> Tuple[List[List[str]], List[str], List[str]]:
        if ue.implementation == UEImplementation.SRS_4G:
            FolderManager.create_native_build_folder(self.setup_cfg.environment.build_dir, "srsRAN_4G")
            return [
                ['cmake', '-DCMAKE_CXX_FLAGS="-Wno-error=array-bounds"', '..'],
                ['make', '-j', str(os.cpu_count())]
            ], [self.setup_cfg.environment.build_dir, 'srsRAN_4G', "build"], SRSRAN_4G_UE_DEPENDENCIES_LINUX
        else:
            logging.error("The selected UE implementation is not supported. Currently, only srsUE is supported.")
            return [], [], []

    def install_dependencies(self, dependencies: List[str]) -> bool:
        log_path = self._setup_logging("srsRAN_4G_dependencies")
        with open(log_path, "w") as log_file:
            if get_operating_system() == OperatingSystem.LINUX:
                commands = [
                    ['sudo', 'apt-get', 'update'],
                    ['sudo', 'apt-get', 'install', '-y'] + dependencies
                ]
            elif get_operating_system() == OperatingSystem.MACOS:
                logging.error("UE cannot be natively built on Mac OS. Please select Docker as build type!")
                return False
            elif get_operating_system() == OperatingSystem.WINDOWS:
                logging.error("UE cannot be natively built on Windows. Please select Docker as build type!")
                return False

            for command in commands:
                logging.warning(f"Install dependencies globally: {dependencies}")
                if not BuildRunner._command_helper(self.setup_cfg.environment.build_dir, "srsUE dependencies",
                                                   command, log_file, log_path):
                    logging.error(f"srsUE dependencies installation failed. See %s for details.", log_path)
                    return False
        return True

    def build_ues(self) -> bool:
        """
        Build the gNB and UE components based on the specified build types.
        Returns: None
        """
        logging.info("Running UE build process...")
        os.chdir(self.setup_cfg.environment.build_dir)
        already_build_natively = False
        for ue in self.setup_cfg.ue:
            if ue.build_type == BuildType.DOCKER:
                logging.info(f"Building UE ({ue.name}) using Docker...")
                ue_ret = self._build_docker_compose('ue', ["docker", "compose", "build", ue.name])
                if not ue_ret:
                    return False
            elif ue.build_type == BuildType.NATIVE and not already_build_natively:
                logging.info(f"Building UE ({ue.name}) native...")
                already_build_natively = True
                build_commands, working_dir, dependencies = self.get_ue_impl_specific_config(ue)
                if not build_commands:
                    return False
                if not self.install_dependencies(dependencies):
                    return False

                ue_ret = self._build_native(working_dir, ue.name, build_commands)
                if not ue_ret:
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
