import logging
import sys
import pathlib

from api.api_endpoints import start_api_server
from main_utils import patch_firmware, build_firmware, run_demo, checkout_repositories

sys.path.insert(0, str(pathlib.Path(__file__).parent.resolve()))

from model.dialog_cfg import DialogConfig
from model.utils_config import FILE_DIR, DEFAULT_CFG_FILE, DEFAULT_DEMO_CFG_FILE

from controller.parser.config_parser import ConfigParser
from view.dialog import setup_logging, print_start_dialog, run_dialog, parse_command_line_arguments

if __name__ == "__main__":
    sys.path.append(FILE_DIR)
    setup_logging()
    if not '--suppress_welcome_header' in sys.argv:
        print_start_dialog()
    cmd_line_cfg = parse_command_line_arguments(sys.argv)

    if len(sys.argv) > 1:
        dialog_cfg = DialogConfig()
        if not cmd_line_cfg.start_fast_api_server:
            if cmd_line_cfg.config_file is None:
                print("Error: No configuration file provided. Specify with --config_file=<path>\n""Exit Program ...")
                exit(1)
            else:
                config = ConfigParser.parse_config_file(cmd_line_cfg.config_file)
    else:
        dialog_cfg = run_dialog()
        config = ConfigParser.parse_config_file(DEFAULT_CFG_FILE)

    if cmd_line_cfg.start_fast_api_server:
        start_api_server()
    else:
        if cmd_line_cfg.run_demo:
            config.programs = ConfigParser.parse_program_setup_config(DEFAULT_DEMO_CFG_FILE, config.environment.build_dir)
            config.verify_consistency()

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
