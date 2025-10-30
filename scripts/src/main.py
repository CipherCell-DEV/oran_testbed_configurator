import logging
import sys
import pathlib

from controller.component_checkout_manager import ComponentCheckoutManager
from view.live_console_view import LiveView

sys.path.insert(0, str(pathlib.Path(__file__).parent.resolve()))

import os

from model.dialog_cfg import DialogConfig
from model.setup_configuration import SetupConfiguration
from model.utils_config import FILE_DIR, DEFAULT_CFG_FILE, DEFAULT_DEMO_CFG_FILE

from controller.builder.build_runner import BuildRunner
from controller.parser.config_parser import ConfigParser
from controller.demo_runner import DemoRunner
from controller.patcher.firmware_patcher import FirmwarePatcher
from view.dialog import setup_logging, print_start_dialog, run_dialog, parse_command_line_arguments


def patch_firmware(setup_cfg: SetupConfiguration):
    """
    Apply required firmware and Docker image patches for the demo environment.
    """
    print("\n***********Patch Components***********\n")
    fw_patcher = FirmwarePatcher(setup_configuration=setup_cfg,
                                 patch_file_path=os.path.join(FILE_DIR, "../..", "patches"))

    if not fw_patcher.patch_single_docker_compose():
        return False

    fw_patcher.copy_files_to_location()
    return True, fw_patcher.get_images_to_push()


def build_firmware(setup_cfg: SetupConfiguration, images_to_push: list[str]) -> bool:
    """
    Build all software components required for the demo (RIC, 5G Core, gNB/UE).
    """
    print("\n***********Build Components***********\n")
    build_runner = BuildRunner(setup_configuration=setup_cfg)

    if setup_cfg.dialog.build_near_rt_ric:
        if not build_runner.build_ric():
            return False

    if setup_cfg.dialog.build_core_net:
        if not build_runner.build_5g_core():
            return False

    if setup_cfg.dialog.build_gnb:
        if not build_runner.build_gnb():
            return False

    if setup_cfg.dialog.build_ue:
        if not build_runner.build_ues():
            return False

    if not build_runner.push_images(images_to_push):
        return False

    return True


def run_demo(setup_cfg: SetupConfiguration):
    """
    Start the demo environment and launch the live console viewer.
    """
    print("\n***********Run Demo***********\n")
    demo_runner = DemoRunner(setup_cfg)
    demo_runner.create_programs()
    view = LiveView(demo_runner)
    view.setup()
    view.start_programs()
    view.connect_view()

    #live_view = LiveConsoleViewer(demo_runner=demo_runner)
    #live_view.start_live_display_loop()


def checkout_repositories(setup_cfg: SetupConfiguration):
    """
    Clone (check out) all repositories required for the current setup configuration.
    """
    component_checkout_mgr = ComponentCheckoutManager(setup_config=setup_cfg)
    component_checkout_mgr.checkout_ric()
    component_checkout_mgr.checkout_5g_core()
    component_checkout_mgr.checkout_gnb()
    component_checkout_mgr.checkout_ue()


if __name__ == "__main__":
    sys.path.append(FILE_DIR)
    setup_logging()
    if not '--suppress_welcome_header' in sys.argv:
        print_start_dialog()
    cmd_line_cfg = parse_command_line_arguments(sys.argv)

    if len(sys.argv) > 1:
        dialog_cfg = DialogConfig()
        if cmd_line_cfg.config_file is None:
            print("Error: No configuration file provided. Specify with --config_file=<path>\n""Exit Program ...")
            exit(1)
        config = ConfigParser.parse_config_file(cmd_line_cfg.config_file)
    else:
        dialog_cfg = run_dialog()
        config = ConfigParser.parse_config_file(DEFAULT_CFG_FILE)

    if cmd_line_cfg.run_demo:
        demo_config = ConfigParser.parse_program_setup_config(DEFAULT_DEMO_CFG_FILE, config.environment.build_dir)
        config.programs = demo_config
        if not config.verify_consistency():
            logging.error("Cannot run demo due to mismatching configuration!")

    checkout_repositories(config)
    config.dialog = dialog_cfg

    if cmd_line_cfg.generate_patch_files:
        success, images_to_push = patch_firmware(config)
        if not success:
            logging.error("Could not patch firmware! -> Exit program")
            exit(1)

        firmware_build_success = True
        if cmd_line_cfg.enable_build:
            firmware_build_success = build_firmware(config, images_to_push)
            if not firmware_build_success:
                logging.error("Failed to build firmware! -> Exit Program!")

        if firmware_build_success and cmd_line_cfg.run_demo:
            run_demo(config)
