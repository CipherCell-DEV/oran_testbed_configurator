"""
Python socket-based traffic handlers for persistent connections.

Uses Python scripts for maintaining persistent socket connections,
reducing connection overhead compared to netcat.

This should be the preferred handler for most use cases.
"""

import os
import time
from typing import override

from trafficker.model.traffic_parameters import TrafficParameters
from trafficker.traffic_handler.traffic_handler import TrafficReceiver, TrafficSender


class PySocketReceiver(TrafficReceiver):
    """Python socket server for receiving traffic."""

    @override
    def __init__(self, parameters: TrafficParameters, service_name: str, server_address: str):
        super().__init__(parameters, service_name, server_address)
        if parameters.use_nist:
            self._script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../model', '..',
                                                             'patches', 'templates', 'traffic', 'pysocket_receiver.py'))
        else:
            self._script_path = '/trafficker/pysocket_receiver.py'

    @override
    def start_receiver(self) -> None:
        """
        Start Python socket server.

        Launches pysocket_receiver.py script on target system which creates a persistent socket.

        Raises:
            RuntimeError: If shell process died or server fails to start
        """
        if self._server_running:
            return

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if self.process.poll() is not None:
            raise RuntimeError("Shell process has died, cannot start server")

        if self._parameters.use_nist and self._parameters.nist_vm != 'local':
            self._script_path = self._copy_script_to_remote('pysocket_receiver.py')

        try:
            udp_flag = '--udp' if self._parameters.use_udp else ''
            self._execute_cmd(f'{self._cmd_prefix} python3 {self._script_path} '
                              f'--host {self._server_address} --port {self._server_port} {udp_flag} &')
            time.sleep(0.3)
            self._server_running = self._exec_and_wait_for_marker(
                f'{self._cmd_prefix} ss -lnp | grep ":{self._server_port}"', f':{self._server_port}')

            if not self._server_running:
                print('Starting PySocket server failed.')

        except Exception as e:
            print(f"Failed to start PySocket server: {e}")
            self._server_running = False
            raise

    @override
    def stop_receiver(self) -> None:
        """Stop Python socket server."""
        if not self._server_running:
            return

        if not self.process:
            print("No active session")
            return

        try:
            kill_cmd = f'{self._cmd_prefix} pkill -f "python3 {self._script_path}"'
            self._execute_cmd(f'{kill_cmd}; echo "KILLED"')

            if not self._wait_for_marker('KILLED'):
                print('Failed to stop PySocket server')
            self._server_running = False

        except Exception as e:
            print(f"Error stopping PySocket server: {e}")
            self._server_running = False

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._server_running


class PySocketSender(TrafficSender):
    """Python socket client for sending traffic."""

    @override
    def __init__(self, parameters: TrafficParameters, service_name: str, server_address: str):
        super().__init__(parameters, service_name, server_address)
        if parameters.use_nist:
            self._script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../model', '..',
                                                             'patches', 'templates', 'traffic', 'pysocket_sender.py'))
        else:
            self._script_path = '/trafficker/pysocket_sender.py'

    @override
    def start_session(self) -> None:
        """
        Start session and launch persistent socket sender.

        The sender script maintains a connection and reads packet sizes
        from stdin for efficient repeated transmission.
        """
        super().start_session()

        if self._parameters.use_nist and self._parameters.nist_vm != 'local':
            self._script_path = self._copy_script_to_remote('pysocket_sender.py')

        udp_flag = '--udp' if self._parameters.use_udp else ''
        self._execute_cmd(f'{self._cmd_prefix} python3 {self._script_path} '
                          f'--port {self._server_port} {udp_flag} {self._server_address}')

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
        """
        Send traffic packet by writing size to sender script stdin.

        The persistent sender script reads packet sizes line-by-line
        and sends corresponding random data.

        Args:
            packet_size: Number of bytes to send
            timeout: Timeout in milliseconds (unused for persistent socket)

        Returns:
            True if packet sent successfully, False otherwise
        """
        if packet_size == 0:
            return True

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        try:
            self._execute_cmd(str(packet_size))
            return True
        except Exception as e:
            print(f"PySocket client failed: {e}")
            return False

    @override
    def close_session(self):
        """Close session and terminate sender script."""
        if self.process:
            try:
                self._execute_cmd('exit')
                time.sleep(0.1)
            except Exception as e:
                print(f"Exception occurred while closing PySocketSender session: {e}")
        super().close_session()
