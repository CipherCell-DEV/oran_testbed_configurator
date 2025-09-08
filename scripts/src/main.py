import os
import sys

from scripts.src.controller.build_runner import BuildRunner
from scripts.src.controller.config_parser import ConfigParser
from scripts.src.controller.demo_runner import DemoRunner
from scripts.src.controller.firmware_patcher import FirmwarePatcher
from scripts.src.model.setup_configuration import SetupConfiguration
from scripts.src.view.dialog import setup_logging, print_start_dialog, run_dialog, parse_command_line_arguments
from scripts.src.view.live_console_viewer import LiveConsoleViewer


def patch_firmware(setup_cfg: SetupConfiguration):
    """
    Apply required firmware and Docker image patches for the demo environment.
    """
    fw_patcher = FirmwarePatcher(setup_configuration=setup_cfg,
                                 patch_file_path=os.path.join(os.getcwd(), "patches"))
    fw_patcher.patch_ric_firmware()
    fw_patcher.patch_5g_core()
    fw_patcher.patch_ue_gnb_docker()
    fw_patcher.copy_files_to_location()


def build_firmware(setup_cfg: SetupConfiguration):
    """
    Build all software components required for the demo (RIC, 5G Core, gNB/UE).
    """
    build_runner = BuildRunner(setup_configuration=setup_cfg)

    build_runner.build_ric()
    build_runner.build_5g_core()
    build_runner.build_gnb_ue()


def run_demo(setup_cfg: SetupConfiguration):
    """
    Start the demo environment and launch the live console viewer.
    """
    demo_runner = DemoRunner(setup_cfg)
    demo_runner.create_programs()
    live_view = LiveConsoleViewer(demo_runner=demo_runner)
    live_view.start_live_display_loop()


if __name__ == "__main__":
    setup_logging()
    print_start_dialog()

    if len(sys.argv) > 1:
        cmd_line_cfg = parse_command_line_arguments(sys.argv)
        config = ConfigParser.parse_config_file(cmd_line_cfg.config_file)

        if cmd_line_cfg.generate_patch_files:
            patch_firmware(config)

        if cmd_line_cfg.enable_build:
            build_firmware(config)

        if cmd_line_cfg.run_demo:
            run_demo(config)
    else:
        run_dialog()
