import time
from typing import override

from model.traffic.traffic_handler import TrafficReceiver, TrafficSender


class PySocketReceiver(TrafficReceiver):

    @override
    def start_receiver(self) -> None:
        if self._server_running:
            return

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if self.process.poll() is not None:
            raise RuntimeError("Shell process has died, cannot start server")

        try:
            self._execute_cmd(
                f'{self._cmd_prefix} python3 server.py --host {self._server_address} --port {self._server_port} --udp &')
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

            if self._wait_for_marker('KILLED'):
                print("PySocket server stopped")
            else:
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
    def start_session(self) -> None:
        super().start_session()
        self._execute_cmd(
            f'{self._cmd_prefix} python3 client.py --port {self._server_port} --udp {self._server_address}')

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

    def close_session(self):
        if self.process:
            try:
                self._execute_cmd('exit')
                time.sleep(0.1)
            except:
                pass
        super().close_session()
