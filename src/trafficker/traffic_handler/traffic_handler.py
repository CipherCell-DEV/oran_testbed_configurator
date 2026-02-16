"""
Base classes for traffic handlers.

Provides abstract interfaces for traffic senders and receivers,
with common functionality for session management and command execution.
"""

import logging
import os
import select
import subprocess
import time
from abc import abstractmethod, ABC
from typing import override

from trafficker.model.traffic_parameters import TrafficParameters


class TrafficHandler(ABC):
    """
    Base class for traffic handlers with session management.

    Manages a persistent shell session (via Docker or SSH) for
    executing traffic commands.
    """

    def __init__(self,
                 parameters: TrafficParameters,
                 service_name: str,
                 server_address: str,
                 server_port: int = 5301):
        """
        Initialize traffic handler.

        Args:
            parameters: Global traffic parameters
            service_name: Docker service or container name
            server_address: IP address for traffic
            server_port: Port for traffic (default: 5301)
        """
        self._parameters = parameters
        self.__service_name = service_name
        self._server_address = server_address
        self._server_port = server_port
        self.process = None

    def _execute_cmd(self, cmd: str) -> None:
        """Execute command in the persistent shell session."""
        logging.debug(f"[{self.__service_name}] exec: {cmd.strip()}")
        if not cmd.endswith('\n'):
            cmd += '\n'
        self.process.stdin.write(cmd)
        self.process.stdin.flush()

    def start_session(self) -> None:
        """
        Start a persistent bash session in the container or VM.

        Opens a subprocess with stdin/stdout/stderr pipes for executing
        commands interactively.
        """
        if self.process is not None:
            logging.debug(f"[{self.__service_name}] Session already active, skipping start")
            return

        if self._parameters.use_nist:
            if self._parameters.nist_vm == 'local':
                cmd = ['bash']
                logging.debug(f"[{self.__service_name}] Starting local bash session")
            else:
                cmd = ['ssh', self._parameters.nist_vm]
                logging.debug(f"[{self.__service_name}] Starting SSH session to {self._parameters.nist_vm}")
        else:
            compose_files = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']
            compose_file_exists = any(os.path.isfile(os.path.join(self._parameters.workdir, f)) for f in compose_files)
            if not compose_file_exists:
                raise FileNotFoundError(f"No docker-compose file found in {self._parameters.workdir}")

            cmd = ['docker', 'compose', 'exec', '-T', self.__service_name, 'bash']
            logging.debug(f"[{self.__service_name}] Starting Docker exec session")

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._parameters.workdir
        )
        self.initialize_shell()
        logging.info(f"[{self.__service_name}] Session started")

    def initialize_shell(self):
        """Verify shell is ready by sending echo command."""
        self._execute_cmd('echo READY')
        if not self._wait_for_marker('READY'):
            logging.warning(f"[{self.__service_name}] Shell initialization timed out")

    def close_session(self):
        """Close the persistent session gracefully."""
        if self.process:
            try:
                self._execute_cmd('exit')
                self.process.wait(timeout=2)
            except Exception:
                self.process.terminate()
            finally:
                self.process = None
                logging.info(f"[{self.__service_name}] Session closed")

    def _copy_script_to_remote(self, file_name: str) -> str:
        """
        Copy script file to remote host via SCP.

        Used for NIST testbed when scripts need to be executed remotely.

        Args:
            file_name: Script filename in patches/templates/traffic/

        Returns:
            Absolute path to script on remote host

        Raises:
            FileNotFoundError: If local script doesn't exist
            RuntimeError: If SCP transfer fails
        """
        script_path = os.path.join(os.path.dirname(__file__), '../../model', '..',
                                   'patches', 'templates', 'traffic', file_name)
        script_path = os.path.abspath(script_path)

        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Template script not found: {script_path}")

        if self._parameters.nist_vm.startswith('root@'):
            target_dir = '/root'
        else:
            nist_vm = self._parameters.nist_vm
            target_dir = f'/home/{nist_vm.split("@")[0] if "@" in nist_vm else nist_vm}'

        target_path = f'{target_dir}/{file_name}'

        try:
            scp_cmd = ['scp', script_path, f"{self._parameters.nist_vm}:{target_path}"]
            logging.debug(f"[{self.__service_name}] Copying {file_name} to {self._parameters.nist_vm}:{target_path}")
            result = subprocess.run(scp_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"Failed to copy script to remote host: {result.stderr}")

            logging.debug(f"[{self.__service_name}] Script copied successfully")

        except Exception as e:
            raise RuntimeError(f"Error copying script to remote host: {e}")

        return target_path

    @property
    def _cmd_prefix(self) -> str:
        """Get command prefix for UE network namespace."""
        if self.__service_name.startswith('ue'):
            return (('sudo ' if self._parameters.use_nist else '') + 'ip netns exec ' + self.__service_name)
        else:
            return ''

    def _exec_and_wait_for_marker(self, cmd: str, marker: str, delay_before_check: float = 0.3,
                                  timeout: int = 2) -> bool:
        """
        Execute command and wait for marker string in output.

        Args:
            cmd: Command to execute
            marker: String to look for in output
            delay_before_check: Seconds to wait before checking output
            timeout: Maximum seconds to wait for marker

        Returns:
            True if marker found, False otherwise
        """
        self._execute_cmd(cmd)
        time.sleep(delay_before_check)
        return self._wait_for_marker(marker, timeout)

    def _wait_for_marker(self, marker: str, timeout: int = 2) -> bool:
        """
        Wait for marker string to appear in process output.

        Args:
            marker: String to search for
            timeout: Maximum seconds to wait

        Returns:
            True if marker found, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
            if ready:
                line = self.process.stdout.readline().strip()
                logging.debug(f"[{self.__service_name}] stdout: {line}")
                if line and marker in line:
                    return True
        return False


class TrafficReceiver(TrafficHandler, ABC):
    """Abstract base class for traffic receivers."""

    @override
    def __init__(self, parameters: TrafficParameters, service_name: str, server_address: str, server_port: int = 5301):
        super().__init__(parameters, service_name, server_address, server_port)
        self._server_running = False

    @abstractmethod
    def start_receiver(self) -> None:
        """Start the receiver server."""
        pass

    @abstractmethod
    def stop_receiver(self) -> None:
        """Stop the receiver server."""
        pass


class TrafficSender(TrafficHandler, ABC):
    """Abstract base class for traffic senders."""

    @abstractmethod
    def send_traffic(self, packet_size: int, timeout: int = 100) -> None:
        """
        Send traffic packet.

        Args:
            packet_size: Number of bytes to send
            timeout: Timeout in milliseconds
        """
        pass
