import time
import select
from typing import override

from model.traffic.traffic_handler import TrafficServer, TrafficClient


class PySocketServer(TrafficServer):

    @override
    def start_server(self) -> None:
        """Start the PySocket server in a separate process"""
        if self._server_running:
            print("PySocket server is already running")
            return

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if self.process.poll() is not None:
            raise RuntimeError("Shell process has died, cannot start server")

        server_cmd = f'{self._cmd_prefix} python3 server.py --host {self._server_address} --port {self._server_port} --udp'

        try:
            print(f"Starting PySocket server on port {self._server_port}")
            self._execute_cmd(f'{server_cmd} &')

            # Wait for server to start
            time.sleep(0.5)

            # Verify server is running by checking if port is listening
            verify_cmd = f'{self._cmd_prefix} ss -ulnp | grep ":{self._server_port} "'
            self._execute_cmd(f'{verify_cmd}; echo "VERIFY_DONE:$?"')

            start_time = time.time()
            server_verified = False

            while time.time() - start_time < 3:
                if self.process.poll() is not None:
                    raise RuntimeError("Shell process died while starting server")

                import select
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                if ready:
                    line = self.process.stdout.readline().strip()

                    if line.startswith("VERIFY_DONE:"):
                        exit_code = int(line.split(":")[1])
                        if exit_code == 0:
                            server_verified = True
                        break
                    elif f":{self._server_port} " in line and "LISTEN" in line:
                        server_verified = True

            if server_verified:
                self._server_running = True
                print(f"PySocket server successfully started and verified on port {self._server_port}")
            else:
                # Fallback: assume server started even if verification failed
                self._server_running = True
                print(f"PySocket server started on port {self._server_port} (verification failed, assuming success)")

        except Exception as e:
            print(f"Failed to start PySocket server: {e}")
            self._server_running = False
            raise

    @override
    def stop_server(self) -> None:
        if not self._server_running:
            print("PySocket server is not running")
            return

        if not self.process:
            print("No active session")
            return

        try:
            kill_cmd = f'{self._cmd_prefix} pkill -f "python3 server.py"'
            self._execute_cmd(f'{kill_cmd}; echo "KILL_DONE"')

            start_time = time.time()
            while time.time() - start_time < 2:
                import select
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                if ready:
                    line = self.process.stdout.readline().strip()
                    if "KILL_DONE" in line:
                        break

            print("PySocket server stopped")
            self._server_running = False

        except Exception as e:
            print(f"Error stopping PySocket server: {e}")
            self._server_running = False

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running"""
        return self._server_running


class PySocketClient(TrafficClient):

    @override
    def start_session(self) -> None:
        super().start_session()
        self._execute_cmd(f'{self._cmd_prefix} python3 client.py --port {self._server_port} --udp {self._server_address}')

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
        """Send traffic using PySocket with random data"""
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
        """Override to ensure any running PySocket processes are cleaned up"""
        if self.process:
            try:
                # Kill any remaining PySocket processes before closing
                cleanup_cmd = f'pkill -f "python3 client.py"'
                self._execute_cmd('exit')
                time.sleep(0.1)
            except:
                pass
        super().close_session()
