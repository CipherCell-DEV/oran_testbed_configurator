from typing import Optional

from controller.patcher.patcher_utils import PatcherUtils
from controller.patcher.single_patcher_base import SinglePatcherBase
from model.setup_configuration import SetupConfiguration


class GenericPatcher(SinglePatcherBase):
    def __init__(self, patch_file_path: str, setup_cfg: SetupConfiguration, patcher_utils: PatcherUtils):
        super().__init__(patch_file_path, setup_cfg, patcher_utils)

    def patch(self):
        pass

    def patch_config_file(self):
        pass

    def patch_docker_compose(self) -> Optional[dict]:
        return None

    def copy_config_files(self):
        super().copy_helper(
            [[self._patch_file_path, "patched", "docker"], [self._patch_file_path, "patched", "config"]],
            ["docker_combined.yml", ".env"],
            [[self._setup_cfg.environment.build_dir], [self._setup_cfg.environment.build_dir]],
            ["docker-compose.yml", ".env"])
