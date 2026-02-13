import logging
import os
import subprocess
from typing import Optional

from api.api_state import LogQueue
from controller.builder.docker.ric_docker_build_runner import NearRTRICDockerBuildRunner
from controller.builder.native.ric_native_build_runner import NearRTRICNativeBuildRunner

from controller.builder.docker.core_5g_docker_build_runner import Core5GDockerBuildRunner
from controller.builder.native.core_5g_native_build_runner import Core5GNativeBuildRunner

from controller.builder.docker.gnb_docker_build_runner import GNBDockerBuildRunner
from controller.builder.native.gnb_native_build_runner import GNBNativeBuildRunner

from controller.builder.docker.ue_docker_build_runner import UEDockerBuildRunner
from controller.builder.native.ue_native_build_runner import UENativeBuilder

from model.setup_configuration import SetupConfiguration
from model.utils_config import BuildType


class BuildRunner:
    """
    Class to handle the build process of RIC, 5G Core, gNB, and UE components.
    It supports both Docker-based and native builds.
    """

    def __init__(self, setup_configuration: SetupConfiguration):
        self.setup_cfg = setup_configuration

    def _build_helper(self, component_cfg, docker_builder_cls, native_builder_cls,
                      log_buffer: Optional[LogQueue] = None) -> bool:
        """
        Generic build method for components that support DOCKER and NATIVE build types.
        """
        builder_cls = docker_builder_cls if component_cfg.build_type == BuildType.DOCKER else native_builder_cls
        builder = builder_cls(self.setup_cfg)
        return builder.build(log_buffer)

    def build_ric(self, log_buffer: Optional[LogQueue] = None) -> bool:
        """
        Build the RIC component based on the specified implementation and build type.
        Returns: None
        """
        logging.info("Running near RT RIC build process...")
        return self._build_helper(
            self.setup_cfg.get_used_ric(),
            NearRTRICDockerBuildRunner,
            NearRTRICNativeBuildRunner,
            log_buffer
        )

    def build_5g_core(self, log_buffer: Optional[LogQueue] = None) -> bool:
        """
        Build the 5G Core Network component based on the specified implementation and build type.
        Returns:
        """
        logging.info("Running 5g core build process...")
        return self._build_helper(
            self.setup_cfg.get_used_ric(),
            Core5GDockerBuildRunner,
            Core5GNativeBuildRunner,
            log_buffer
        )

    def build_gnb(self, log_buffer: Optional[LogQueue] = None) -> bool:
        """
        Build the gNB and UE components based on the specified build types.
        Returns: None
        """
        logging.info("Running gNB build process...")
        return self._build_helper(
            self.setup_cfg.get_used_ric(),
            GNBDockerBuildRunner,
            GNBNativeBuildRunner,
            log_buffer
        )

    def build_ues(self, log_buffers: Optional[list[LogQueue]] = None) -> bool:
        """
        Build the gNB and UE components based on the specified build types.
        Returns: None
        """
        logging.info("Running UE build process...")
        curr_dir = os.getcwd()
        os.chdir(self.setup_cfg.environment.build_dir)

        already_build_natively = False
        if log_buffers is None:
            log_buffers = [None] * len(self.setup_cfg.ue.ues)

        for ue, log_buffer in zip(self.setup_cfg.ue.ues, log_buffers):
            if ue.build_type == BuildType.DOCKER:
                if not UEDockerBuildRunner(self.setup_cfg, ue).build(log_buffer):
                    os.chdir(curr_dir)
                    return False
            elif ue.build_type == BuildType.NATIVE and not already_build_natively:
                already_build_natively = True
                if not UENativeBuilder(self.setup_cfg, ue).build():
                    os.chdir(curr_dir)
                    return False
        os.chdir(curr_dir)
        return True

    def push_images(self, images_to_push: list[str]) -> bool:
        """
        Push specified Docker images to the registry, if push_local_images is enabled.

        Args:
            images_to_push (list[str]): List of Docker image names to push.

        Returns:
            bool: True if all images were successfully pushed or pushing is disabled, False otherwise.
        """
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
