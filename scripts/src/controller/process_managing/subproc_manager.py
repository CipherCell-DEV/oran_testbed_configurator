import logging
import subprocess

from demo_runner import DemoRunner
from process_manager_base import ProcessManager

class SubprocessManager(ProcessManager):
    def __init__(self, runner : DemoRunner):
        super().__init__(runner)

    def cleanup_and_shutdown(self):
        """Stop all Docker containers using docker compose down (If running using docker)"""
        working_dir = self.demo_runner.cfg.environment.build_dir

        try:
            logging.info("Stopping all Docker containers...")
            result = subprocess.run(
                ["docker", "compose", "down"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logging.info("All containers stopped successfully.")
            else:
                logging.warning(f"Docker compose down returned non-zero exit code: {result.returncode}")
                logging.warning(f"stderr: {result.stderr}")
        except subprocess.TimeoutExpired:
            logging.error("Timeout while stopping containers. Forcing container termination...")
            subprocess.run(["docker", "compose", "kill"], cwd=working_dir, capture_output=True)
        except Exception as e:
            logging.error(f"Error stopping containers: {e}")