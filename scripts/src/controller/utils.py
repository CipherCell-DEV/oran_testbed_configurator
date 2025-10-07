import logging
import subprocess
from enum import Enum
import platform


def check_docker_compose_daemon_is_running() -> bool:
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        logging.error("Docker does not appear to be running. Please start Docker before building components.")
        return False


class OperatingSystem(Enum):
    LINUX = "Linux"
    MACOS = "Darwin"
    WINDOWS = "Windows"


def get_operating_system():
    os_name = platform.system()
    if os_name == OperatingSystem.LINUX.value:
        return OperatingSystem.LINUX
    elif os_name == OperatingSystem.MACOS.value:
        return OperatingSystem.MACOS
    elif os_name == OperatingSystem.WINDOWS.value:
        return OperatingSystem.WINDOWS
    else:
        raise ValueError(f"Unsupported operating system: {os_name}")
