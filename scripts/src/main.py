import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.resolve()))

import os

from model.dialog_cfg import DialogConfig
from model.setup_configuration import SetupConfiguration
from model.utils_config import FILE_DIR, DEFAULT_CFG_FILE

from controller.build_runner import BuildRunner
from controller.config_parser import ConfigParser
from controller.demo_runner import DemoRunner
from controller.firmware_patcher import FirmwarePatcher
from view.dialog import setup_logging, print_start_dialog, run_dialog, parse_command_line_arguments
from view.live_console_viewer import LiveConsoleViewer


def patch_firmware(setup_cfg: SetupConfiguration, dialog_config: DialogConfig):
    """
    Apply required firmware and Docker image patches for the demo environment.
    """
    fw_patcher = FirmwarePatcher(setup_configuration=setup_cfg,
                                 patch_file_path=os.path.join(FILE_DIR, "../..", "patches"))

    if dialog_config.build_near_rt_ric:
        fw_patcher.patch_ric_firmware()

    if dialog_config.build_core_net:
        fw_patcher.patch_5g_core()

    if dialog_config.build_gnb:
        fw_patcher.patch_ue_gnb_docker()

    fw_patcher.copy_files_to_location()


def build_firmware(setup_cfg: SetupConfiguration, dialog_config: DialogConfig):
    """
    Build all software components required for the demo (RIC, 5G Core, gNB/UE).
    """
    build_runner = BuildRunner(setup_configuration=setup_cfg)

    if dialog_config.build_near_rt_ric:
        build_runner.build_ric()

    if dialog_config.build_core_net:
        build_runner.build_5g_core()

    if dialog_config.build_ue:
        build_runner.build_gnb_ue()


def run_demo(setup_cfg: SetupConfiguration, dialog_cfg: DialogConfig):
    """
    Start the demo environment and launch the live console viewer.
    """
    demo_runner = DemoRunner(setup_cfg)
    demo_runner.create_programs()
    live_view = LiveConsoleViewer(demo_runner=demo_runner)
    live_view.start_live_display_loop()


if __name__ == "__main__":
    sys.path.append(FILE_DIR)
    setup_logging()
    print_start_dialog()
    cmd_line_cfg = parse_command_line_arguments(sys.argv)

    if len(sys.argv) > 1:
        dialog_cfg = DialogConfig()
        print(cmd_line_cfg.config_file)
        config = ConfigParser.parse_config_file(cmd_line_cfg.config_file)
    else:
        dialog_cfg = run_dialog()
        config = ConfigParser.parse_config_file(DEFAULT_CFG_FILE)

    if cmd_line_cfg.generate_patch_files:
        patch_firmware(config, dialog_cfg)

    if cmd_line_cfg.enable_build:
        build_firmware(config, dialog_cfg)

    if cmd_line_cfg.run_demo:
        run_demo(config, dialog_cfg)
