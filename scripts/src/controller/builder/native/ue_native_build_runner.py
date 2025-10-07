import logging
import os
from typing import Tuple, List

from controller.builder.native.native_builder_base import NativeBuilderBase
from controller.folder_manager import FolderManager
from model.setup_configuration import SetupConfiguration
from model.ue_config import UEImplementation, UECfg, SRSRAN_4G_UE_DEPENDENCIES_LINUX

UE_LOG_NAME = "ue_native_build"


class UENativeBuilder(NativeBuilderBase):
    def __init__(self, setup_cfg: SetupConfiguration, ue: UECfg):
        super().__init__(setup_cfg)
        self._ue = ue

    def build(self):
        logging.info(f"Building UE ({self._ue.name}) native...")
        build_commands, working_dir, dependencies = self.get_implementation_specific_config()
        if not build_commands:
            return False
        if not self.install_dependencies(UE_LOG_NAME, dependencies):
            return False

        ue_ret = self.build_helper(working_dir, self._ue.name, build_commands)
        if not ue_ret:
            return False

    def get_implementation_specific_config(self) -> Tuple[List[List[str]], List[str], List[str]]:
        if self._ue.implementation == UEImplementation.SRS_4G:
            FolderManager.create_native_build_folder(self.setup_cfg.environment.build_dir, "srsRAN_4G")
            return [
                ['cmake', '-DCMAKE_CXX_FLAGS="-Wno-error=array-bounds"', '..'],
                ['make', '-j', str(os.cpu_count())]
            ], [self.setup_cfg.environment.build_dir, 'srsRAN_4G', "build"], SRSRAN_4G_UE_DEPENDENCIES_LINUX
        else:
            logging.error("The selected UE implementation is not supported. Currently, only srsUE is supported.")
            return [], [], []
