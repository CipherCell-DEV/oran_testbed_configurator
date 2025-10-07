import logging
import os
from abc import ABCMeta, abstractmethod
from typing import Tuple, List

from controller.builder.builder_base import BuilderBase
from controller.utils import get_operating_system, OperatingSystem
from model.setup_configuration import SetupConfiguration


class NativeBuilderBase(BuilderBase, metaclass=ABCMeta):
    def __init__(self, setup_cfg: SetupConfiguration):
        super().__init__(setup_cfg)

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def get_implementation_specific_config(self) -> Tuple[List[List[str]], List[str], List[str]]:
        pass

    def install_dependencies(self, dependencies_log_name: str, dependencies: List[str]) -> bool:
        log_path = self.utils.setup_logging(dependencies_log_name)
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

            logging.warning(f"Install dependencies globally: {dependencies}")
            for command in commands:
                if not self.utils.command_helper(self.setup_cfg.environment.build_dir, "srsUE dependencies",
                                                 command, log_file, log_path):
                    logging.error(f"srsUE dependencies installation failed. See %s for details.", log_path)
                    return False
        return True

    def build_helper(self, working_dir: List[str], component_name: str, command_list: List[List[str]]):
        log_path = self.utils.setup_logging(component_name)
        full_working_dir = str(os.path.join(*working_dir))
        with open(log_path, "w") as log_file:
            for command in command_list:
                if not self.utils.command_helper(full_working_dir, component_name, command, log_file, log_path):
                    logging.error(f"{component_name} native build failed. See %s for details.", log_path)
                    return False
            return True
