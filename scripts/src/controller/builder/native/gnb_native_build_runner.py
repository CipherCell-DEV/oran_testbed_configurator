import logging
import os
from typing import Tuple, List

from controller.builder.native.native_builder_base import NativeBuilderBase
from controller.folder_manager import FolderManager
from model.gnb_config import GNBImplementation, SRSRAN_GNB_DEPENDENCIES_LINUX
from model.setup_configuration import SetupConfiguration

UE_LOG_NAME = "gnb_native_build"


class GNBNativeBuildRunner(NativeBuilderBase):
    def __init__(self, setup_cfg: SetupConfiguration):
        super().__init__(setup_cfg)

    def build(self) -> bool:
        logging.info(f"Building gNB native...")
        build_commands, working_dir, dependencies = self.get_implementation_specific_config()
        if not build_commands:
            return False

        if not self.install_dependencies(UE_LOG_NAME, dependencies):
            return False

        return self.build_helper(working_dir, "gnb", build_commands)

    def get_implementation_specific_config(self) -> Tuple[List[List[str]], List[str], List[str]]:
        if self.setup_cfg.gnb.implementation == GNBImplementation.SRS:
            FolderManager.create_native_build_folder(self.setup_cfg.environment.build_dir, "srsRAN_Project")
            return [
                ['cmake', '-DENABLE_UHD=OFF', '-DENABLE_ARMPL=OFF', '-DENABLE_EXPORT=ON', '-DENABLE_ZEROMQ=ON', '..'],
                ['make', '-j', str(os.cpu_count())]
            ], [self.setup_cfg.environment.build_dir, 'srsRAN_Project', "build"], SRSRAN_GNB_DEPENDENCIES_LINUX
        else:
            logging.error("The selected gNB implementation is not supported. Currently, only srsGNB is supported.")
            return [], [], []
