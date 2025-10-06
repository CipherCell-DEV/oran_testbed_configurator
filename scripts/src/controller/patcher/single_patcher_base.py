import logging
import os
import shutil
from abc import ABCMeta, abstractmethod
from typing import List, Optional

from controller.patcher.patcher_utils import PatcherUtils
from model.setup_configuration import SetupConfiguration


class SinglePatcherBase(metaclass=ABCMeta):
    def __init__(self, patch_file_path: str, setup_config: SetupConfiguration, patcher_utils: PatcherUtils):
        self._patch_file_path = patch_file_path
        self._setup_cfg = setup_config
        self._patcher_utils = patcher_utils

    @abstractmethod
    def patch(self):
        pass

    @abstractmethod
    def patch_docker_compose(self) -> Optional[dict]:
        pass

    def copy_config_files(self):
        pass

    def patch_config_file(self):
        pass

    def patch_env_file(self, env_dict: dict) -> dict:
        return env_dict

    def copy_helper(self, path_list_src: List[List[str]], file_name_list_src: List[str], path_list_dst: List[List[str]],
                    file_name_list_dst: List[str]):
        logging.info("Copying patched files to build directory...")

        file_mappings = list(map(lambda path_src, file_src, path_dst, file_dst: (os.path.join(*path_src, file_src),
                                                                                 os.path.join(*path_dst, file_dst)),
                                 path_list_src, file_name_list_src, path_list_dst, file_name_list_dst))

        for src, dst in file_mappings:
            try:
                logging.info("Copy file from %s to %s", src, dst)
                shutil.copy(src, dst)
                src = src.replace(f'{self._patch_file_path}' + '/', '')
                dst = dst.replace(f'{self._setup_cfg.environment.build_dir}' + '/', '')
            except FileNotFoundError:
                logging.error("Source file not found: %s", src)
                raise
            except PermissionError:
                logging.error("Permission denied while copying %s to %s", src, dst)
                raise
            except Exception:
                logging.exception("Unexpected error while copying %s to %s", src, dst)
                raise
