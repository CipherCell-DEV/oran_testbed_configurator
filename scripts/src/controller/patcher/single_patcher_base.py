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

    @staticmethod
    def copy_helper(path_list_src: List[List[str]], file_name_list_src: List[str],
                    path_list_dst: List[List[str]], file_name_list_dst: List[str]):
        """
        Copy multiple files from source to destination directories.
        
        This method iterates through lists of source and destination paths, copying each file
        while creating necessary destination directories. Progress is logged for each file.
        
        Args:
            path_list_src: List of path component lists for source directories.
                          Example: [['path', 'to', 'dir1'], ['path', 'to', 'dir2']]
            file_name_list_src: List of source file names corresponding to path_list_src.
                               Example: ['file1.txt', 'file2.yaml']
            path_list_dst: List of path component lists for destination directories.
                          Example: [['build', 'output', 'dir1'], ['build', 'output', 'dir2']]
            file_name_list_dst: List of destination file names corresponding to path_list_dst.
                               Example: ['file1.txt', 'config.yaml']
        """
        for index in range(len(file_name_list_src)):
            source_path = os.path.join(*path_list_src[index], file_name_list_src[index])
            destination_path = os.path.join(*path_list_dst[index], file_name_list_dst[index])

            try:
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                shutil.copy(source_path, destination_path)
            except Exception:
                logging.exception("Error copying %s to %s", source_path, destination_path)
                raise
0