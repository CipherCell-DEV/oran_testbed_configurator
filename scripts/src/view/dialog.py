import logging
import os
import sys
from typing import List

from model.dialog_cfg import DialogConfig, CommandLineConfig
from model.utils_config import BuildType, FILE_DIR

LOG_COLORS = {
    "DEBUG": "\033[37m",  # White
    "INFO": "\033[36m",  # Cyan
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
}
RESET_COLOR = "\033[0m"


class LevelColorFormatter(logging.Formatter):
    def format(self, record):
        log_color = LOG_COLORS.get(record.levelname, "")
        record.levelname = f"{log_color}{record.levelname}{RESET_COLOR}"
        return super().format(record)


def setup_logging():
    # Setup logging with color formatter
    handler = logging.StreamHandler()
    handler.setFormatter(LevelColorFormatter("%(asctime)s [%(levelname)s] %(message)s"))

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


def ask_choice(prompt, options, default=None):
    """Ask user to choose from numbered options."""
    while True:
        print(prompt)
        for i, opt in enumerate(options, 1):
            print(f"{i}: {opt}")
        choice = input(f"Enter choice (1-{len(options)}): ").strip()
        if not choice and default:
            return default
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice)
        print("Invalid choice. Try again.\n")


def ask_yes_no(prompt, default=None):
    """Ask user yes/no question."""
    while True:
        choice = input(f"{prompt} (y/n): ").strip().lower()
        if not choice and default is not None:
            return default
        if choice in ("y", "n"):
            return choice == "y"
        print("Invalid input. Enter 'y' or 'n'.\n")


def run_dialog() -> DialogConfig:
    dialog_config = DialogConfig()

    print("Running interactive configuration dialog using default parameters\n")

    build_type = ask_choice("Choose your build type:", ["Docker", "Native"], default=1)
    if build_type == 1:
        dialog_config.build_type = BuildType.DOCKER
    else:
        dialog_config.build_type = BuildType.NATIVE

    compile_all = ask_yes_no("Compile all components?", default=False)
    if not compile_all:
        dialog_config.build_near_rt_ric = ask_yes_no("Compile oran sc ric?", default=False)
        dialog_config.build_core_net = ask_yes_no("Compile 5g core network?", default=False)
        dialog_config.build_gnb = ask_yes_no("Compile gnb network?", default=False)
        dialog_config.build_ue = ask_yes_no("Compile srs ran 4G?", default=False)
    else:
        print("Compiling all components...")

    return dialog_config


def print_start_dialog():
    print("\n**************************************************")
    print("*****    Starting CipherCell Configurator     ****")
    print("**************************************************\n")


def print_help() -> None:
    """
    Print command line usage instructions and exit.
    """
    help_text = """
Usage:
    python main.py [options]

Options:
    --config_file=<path>         Path to the YAML/JSON configuration file.
    --patching=<true|false>      Enable or disable firmware patch generation.
    --build_components=<true|false>
                               Enable or disable build step.
    --run_demo=<true|false>      Enable or disable demo execution.

    --help                     Show this help message and exit.

Examples:
    python main.py --config_file=./configs/sample.yaml --patching=true --build_components=false --run_demo=true
    python main.py --help
"""
    print(help_text.strip())
    sys.exit(0)


def parse_command_line_arguments(argv: List[str]) -> CommandLineConfig:
    cfg = CommandLineConfig()

    def parse_boolean_value(value: str) -> bool:
        return value.casefold() in ("true", "1", "yes", "on")

    for v in argv[1:]:

        if v.startswith("--help"):
            print_help()

        if v.startswith("--api_endpoint="):
            cfg.start_fast_api_server = parse_boolean_value(v.split("=", 1)[1])
            logging.info(f"Enable FastAPI Endpoint: {cfg.generate_patch_files}")
        elif v.startswith("--config_file="):
            cfg.config_file = v.split("=", 1)[1]
            if not cfg.config_file.startswith('/'):
                cfg.config_file = os.path.join(FILE_DIR, "../..", cfg.config_file)
            if not os.path.exists(cfg.config_file):
                raise ValueError(f"Config file does not exist: {cfg.config_file}")
            logging.info(f"Using configuration file: {cfg.config_file}")

        elif v.startswith("--patching="):
            cfg.generate_patch_files = parse_boolean_value(v.split("=", 1)[1])
            logging.info(f"Patching enabled: {cfg.generate_patch_files}")

        elif v.startswith("--build_components="):
            cfg.enable_build = parse_boolean_value(v.split("=", 1)[1])
            logging.info(f"Build enabled: {cfg.enable_build}")

        elif v.startswith("--run_demo="):
            cfg.run_demo = parse_boolean_value(v.split("=", 1)[1])
            logging.info(f"Run demo: {cfg.run_demo}")
        elif v.startswith("--suppress_welcome_header"):
            pass
        else:
            logging.warning(f"Ignoring unrecognized argument: {v}")

    return cfg
