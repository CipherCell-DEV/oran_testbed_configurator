import logging
from typing import Tuple, List

from controller.builder.native.native_builder_base import NativeBuilderBase
from model.setup_configuration import SetupConfiguration


class Core5GNativeBuildRunner(NativeBuilderBase):

    def __init__(self, setup_cfg: SetupConfiguration):
        super().__init__(setup_cfg)

    def build(self):
        logging.error("Building 5G Core natively is not supported at the moment.")
        return False

    def get_implementation_specific_config(self) -> Tuple[List[List[str]], List[str], List[str]]:
        pass
