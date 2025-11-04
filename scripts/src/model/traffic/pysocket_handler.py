import os
import time
from typing import override

from model.traffic.traffic_config import TrafficParameters
from model.traffic.traffic_handler import TrafficReceiver, TrafficSender


class PySocketReceiver(TrafficReceiver):

    @override
    def __init__(self, parameters: TrafficParameters, service_name: str, server_address: str):
        super().__init__(parameters, service_name, server_address)
        self._script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..',
                                                         'patches', 'templates', 'traffic', 'pysocket_receiver.py'))

    @override
    def start_receiver(self) -> None:
        if self._server_running:
            return

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if self.process.poll() is not None:
            raise RuntimeError("Shell process has died, cannot start server")

        if self._parameters.use_nist and self._parameters.nist_vm != 'local':
            self._script_path = self._copy_script_to_remote('pysocket_receiver.py')

        try:
            self._execute_cmd(
                f'{self._cmd_prefix} python3 {self._script_path} --host {self._server_address} --port {self._server_port} --udp &')
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
        if not self._server_running:
            return

        if not self.process:
            print("No active session")
            return

        try:
            kill_cmd = f'{self._cmd_prefix} pkill -f "python3 server.py"'
            self._execute_cmd(f'{kill_cmd}; echo "KILLED"')

            if not self._wait_for_marker('KILLED'):
                print('Failed to stop PySocket server')
            self._server_running = False

        except Exception as e:
            print(f"Error stopping PySocket server: {e}")
            self._server_running = False

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running"""
        return self._server_running


class PySocketSender(TrafficSender):

    @override
    def __init__(self, parameters: TrafficParameters, service_name: str, server_address: str):
        super().__init__(parameters, service_name, server_address)
        self._script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..',
                                                         'patches', 'templates', 'traffic', 'pysocket_sender.py'))

    @override
    def start_session(self) -> None:
        super().start_session()

        if self._parameters.use_nist and self._parameters.nist_vm != 'local':
            self._script_path = self._copy_script_to_remote('pysocket_sender.py')

        self._execute_cmd(
            f'{self._cmd_prefix} python3 {self._script_path} --port {self._server_port} --udp {self._server_address}')

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
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
        if self.process:
            try:
                self._execute_cmd('exit')
                time.sleep(0.1)
            except:
                pass
        super().close_session()
