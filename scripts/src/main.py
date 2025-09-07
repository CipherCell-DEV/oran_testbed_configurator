import logging
import os
import sys

from scripts.src.build_runner import BuildRunner
from scripts.src.config_parser import ConfigParser
from scripts.src.firmware_patcher import FirmwarePatcher
from scripts.src.live_console_viewer import LiveConsoleViewer, Program

# Define colors using ANSI escape codes
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


if __name__ == "__main__":
    setup_logging()
    print_start_dialog()
    if len(sys.argv) > 2:
        config_path = sys.argv[1]
        config_file = sys.argv[2]
        path_file = os.path.join(config_path, config_file)
        if os.path.exists(path_file):
            logging.info(f"Using configuration from {config_file}")
            config = ConfigParser.parse_config_file(config_path, config_file)

            fw_patcher = FirmwarePatcher(setup_configuration=config,
                                         patch_file_path=os.path.join(os.getcwd(), "patches"))

            fw_patcher.patch_ric_firmware()
            fw_patcher.patch_5g_core()
            fw_patcher.patch_ue_gnb_docker()
            fw_patcher.copy_files_to_location()

            build_runner = BuildRunner(setup_configuration=config)

            build_runner.build_ric()
            build_runner.build_5g_core()
            build_runner.build_gnb_ue()

            logging.info("Build process completed successfully!")

            live_view = LiveConsoleViewer()

            live_view.thread_pool.add_program(
                Program(working_dir=os.path.join(config.environment.build_dir, 'oran-sc-ric'), name="RIC",
                        command=['docker', 'compose', 'up']))

            live_view.thread_pool.add_program(
                Program(working_dir=os.path.join(config.environment.build_dir, 'srsRAN_Project', 'docker'),
                        name="5G-core",
                        command=['docker', 'compose', 'up', '--build', '5gc']))

            live_view.thread_pool.add_program(
                Program(working_dir=os.path.join(config.environment.build_dir),
                        name="gnb",
                        command=['docker', 'compose', 'up', 'gnb']))

            live_view.thread_pool.add_program(
                Program(working_dir=os.path.join(config.environment.build_dir),
                        name="ue",
                        command=['docker', 'compose', 'up', 'ue']))

            live_view.start_live_display_loop()

            print("All processes finished.")


        else:
            logging.info(f"Error: Config file {config_file} not found.")
            sys.exit(1)
    else:
        run_dialog()
