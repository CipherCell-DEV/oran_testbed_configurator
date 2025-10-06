import logging
import subprocess


def _check_docker_compose_daemon_is_running() -> bool:
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        logging.error("Docker does not appear to be running. Please start Docker before building components.")
        return False
