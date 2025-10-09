import logging
import os
import subprocess
from typing import List

from tqdm import tqdm

from controller.folder_manager import FolderManager
from model.setup_configuration import SetupConfiguration


class BuildUtils:
    def __init__(self, setup_cfg: SetupConfiguration):
        self.setup_cfg = setup_cfg

    def setup_logging(self, component_name: str) -> str:
        FolderManager.create_build_log_dir(self.setup_cfg)
        return os.path.join(self.setup_cfg.environment.log_dir, f"{component_name}.log")

    @staticmethod
    def command_helper(working_dir: str, component_name: str, command: List[str], log_file, log_path: str):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=working_dir
        )

        with tqdm(desc=f"Building {component_name}", unit="line") as pbar:
            for line in process.stdout:
                log_file.write(line)
                pbar.update(1)

        process.wait()
        if process.returncode != 0:
            logging.error(f"{component_name} build failed. See %s for details.", log_path)
            raise subprocess.CalledProcessError(process.returncode, process.args)
        return True
