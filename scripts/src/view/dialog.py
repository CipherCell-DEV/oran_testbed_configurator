# Define colors using ANSI escape codes
import logging
import os
import sys
from typing import List

from scripts.src.model.setup_configuration import CommandLineConfig

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
    logger.setLevel(logging.DEBUG)
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


def detect_platform_and_release():
    import platform
    system = platform.system()
    release = platform.system()
    if system == "Linux":
        return "Linux", release
    elif system == "Darwin":
        return "macOS", release
    elif system == "Windows":
        return "Windows", release
    else:
        return "Unknown"


def run_dialog():
    print("Running interactive configuration dialog using default parameters\n")

    os_type, os_release = detect_platform_and_release()
    print(f"Detected OS: {os_type} {os_release}\n")

    build_type = ask_choice("Choose your build type:", ["Docker", "Native"], default=1)
    print(f"You chose {'Docker' if build_type == 1 else 'Native'} build.")

    compile_all = ask_yes_no("Compile all components?", default=False)
    if not compile_all:
        sc_ric = ask_yes_no("Compile sc ric?", default=False)
        core_net = ask_yes_no("Compile core network?", default=False)
        gnb_net = ask_yes_no("Compile gnb network?", default=False)
        srs_ran_4g = ask_yes_no("Compile srs ran 4G?", default=False)

        if sc_ric:
            print(f"Compile SRC RIC of build type: {build_type}")
            if build_type == 1 and os_type == "macOS":
                print("Patching sc-ric docker-compose.yml for macOS systems")
    else:
        print("Compiling all components...")


def print_start_dialog():
    print("\n**************************************************")
    print("***** Start Building srsRAN test environment *****")
    print("*****             CipherCell                 *****")
    print("**************************************************\n")

def print_help() -> None:
    """
    Print command line usage instructions and exit.
    """
    help_text = """
Usage:
    python main.py [options]

Options:
    config_file=<path>         Path to the YAML/JSON configuration file.
    patching=<true|false>      Enable or disable firmware patch generation.
    build_components=<true|false>
                               Enable or disable build step.
    run_demo=<true|false>      Enable or disable demo execution.

    --help                     Show this help message and exit.

Examples:
    python main.py config_file=./configs/demo.yaml patching=true build_components=false run_demo=true
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

        if v.startswith("config_file="):
            cfg.config_file = v.split("=", 1)[1]
            if not os.path.exists(cfg.config_file):
                raise ValueError(f"Config file does not exist: {cfg.config_file}")
            logging.info(f"Using configuration file: {cfg.config_file}")

        elif v.startswith("patching="):
            cfg.generate_patch_files = parse_boolean_value(v.split("=", 1)[1])
            logging.info(f"Patching enabled: {cfg.generate_patch_files}")

        elif v.startswith("build_components="):
            cfg.enable_build = parse_boolean_value(v.split("=", 1)[1])
            logging.info(f"Build enabled: {cfg.enable_build}")

        elif v.startswith("run_demo="):
            cfg.run_demo = parse_boolean_value(v.split("=", 1)[1])
            logging.info(f"Run demo: {cfg.run_demo}")

        else:
            logging.warning(f"Ignoring unrecognized argument: {v}")

    return cfg