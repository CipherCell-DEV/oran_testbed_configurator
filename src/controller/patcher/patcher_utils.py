import logging
import os
import re
from typing import List

from model.setup_configuration import SetupConfiguration


class PatcherUtils:
    def __init__(self, setup_cfg: SetupConfiguration):
        self._setup_cfg = setup_cfg

    def replace_tag_and_image(self, string: str) -> str:
        string = string.replace("localhost:4000", self._setup_cfg.environment.docker_registry)
        string = string.replace("-selftag", self.get_tag_or_empty_string("-"))
        string = string.replace(":selftag", self.get_tag_or_empty_string(":"))
        return string

    def get_tag_or_empty_string(self, prefix: str) -> str:
        if self._setup_cfg.environment.tag_appendix is None:
            return ""
        else:
            return f"{prefix}{self._setup_cfg.environment.tag_appendix}"

    @staticmethod
    def load_env_file_str_helper(env_file_content: List[str]) -> dict:
        env_dict = {}
        for line in env_file_content:
            # ^ (?!  # ) -> not start with comment
            # \s* → optional leading spaces
            # ([^=]+?) -> Capture everything until =
            # \s*=\s* -> allow optional spaces around =
            # (.*) capture everything after =
            matches = re.findall(r'^(?!#)\s*([^=]+?)\s*=\s*(.*)$', line.strip())
            env_dict.update(dict(matches))
        return env_dict

    @staticmethod
    def patch_env_file(patch_file_path: str, env_dict: dict):
        output_env_file = os.path.join(patch_file_path, "patched", "config", ".env")
        with open(output_env_file, 'w') as patched_env_file:
            for key, value in env_dict.items():
                patched_env_file.write(f'{key}={value}\n')