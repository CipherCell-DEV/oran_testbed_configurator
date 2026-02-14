import logging
from abc import ABCMeta, abstractmethod
from typing import List, Optional

from api.api_state import LogQueue
from controller.builder.builder_base import BuilderBase
from controller.utils import check_docker_compose_daemon_is_running
from model.setup_configuration import SetupConfiguration


class DockerBuilderBase(BuilderBase, metaclass=ABCMeta):
    def __init__(self, setup_cfg: SetupConfiguration):
        super().__init__(setup_cfg)

    @abstractmethod
    def build(self, log_buffer: Optional[LogQueue] = None) -> bool:
        pass

    def docker_compose_build_helper(self, component_name: str, command: List[str],
                                    log_buffer: Optional[LogQueue] = None):
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

        log_path = self.utils.setup_logging(component_name)

        logging.info(f"Building {component_name} using Docker...")
        with open(log_path, "w") as log_file:
            if self.utils.command_helper(self.setup_cfg.environment.build_dir, component_name, command,
                                         log_file, log_path, log_buffer):
                logging.info(f"{component_name} Docker build completed successfully ✅ (log: %s)",
                             log_path)
                print()  # Add empty line to indicate that build is done!
                return True
            else:
                return False
