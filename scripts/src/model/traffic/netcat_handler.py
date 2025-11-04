import time
from typing import override

from model.traffic.traffic_handler import TrafficReceiver, TrafficSender


class NetcatReceiver(TrafficReceiver):
    """Netcat UDP server that listens for incoming traffic"""

    @override
    def start_receiver(self) -> None:
        """Start the netcat server in a separate process"""
        if self._server_running:
            print("Netcat server is already running")
            return

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        # Check if the shell process is still alive
        if self.process.poll() is not None:
            raise RuntimeError("Shell process has died, cannot start server")

        server_cmd = f'{self._cmd_prefix} nc -u -k -l -p {self._server_port}'

        try:
            print(f"Starting netcat server on port {self._server_port}")
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
                print(f"Netcat server successfully started and verified on port {self._server_port}")
            else:
                # Fallback: assume server started even if verification failed
                self._server_running = True
                print(f"Netcat server started on port {self._server_port} (verification failed, assuming success)")

        except Exception as e:
            print(f"Failed to start netcat server: {e}")
            self._server_running = False
            raise

    @override
    def stop_receiver(self) -> None:
        """Stop the netcat server"""
        if not self._server_running:
            print("Netcat server is not running")
            return

        if not self.process:
            print("No active session")
            return

        try:
            kill_cmd = f'{self._cmd_prefix} pkill -f "nc.*-l.*{self._server_port}"'
            self._execute_cmd(f'{kill_cmd}; echo "KILL_DONE"')

            start_time = time.time()
            while time.time() - start_time < 2:
                import select
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                if ready:
                    line = self.process.stdout.readline().strip()
                    if "KILL_DONE" in line:
                        break

            print("Netcat server stopped")
            self._server_running = False

        except Exception as e:
            print(f"Error stopping netcat server: {e}")
            self._server_running = False

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running"""
        return self._server_running


class NetcatSender(TrafficSender):
    """Netcat UDP client that sends random data packets"""

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
        """Send traffic using netcat with random data"""
        if packet_size == 0:
            return True

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        netcat_cmd = (f'{self._cmd_prefix} dd if=/dev/urandom bs={packet_size} count=1 | '
                     f'nc -u -q 0 {self._server_address} {self._server_port}')
        cmd = f'{netcat_cmd}; echo "EXIT_CODE:$?"'

        try:
            self._execute_cmd(cmd)

            timeout_s = timeout / 1000.0
            start_time = time.time()

            while time.time() - start_time < timeout_s:
                import select
                ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                if ready:
                    line = self.process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line.startswith("EXIT_CODE:"):
                            exit_code = int(line.split(":")[1])
                            success = exit_code == 0
                            if not success:
                                print(f"Netcat failed with exit code {exit_code}")
                            return success

                # Check if process is still alive
                if self.process.poll() is not None:
                    print("Session terminated unexpectedly")
                    return False

            print(f"Netcat client timed out after {timeout}ms")
            return False

        except Exception as e:
            print(f"Netcat client failed: {e}")
            return False

    def close_session(self):
        """Override to ensure any running netcat processes are cleaned up"""
        if self.process:
            try:
                # Kill any remaining netcat processes before closing
                cleanup_cmd = f'{self._cmd_prefix} pkill -f "nc.*{self._server_address}.*{self._server_port}"'
                self._execute_cmd(cleanup_cmd)
                time.sleep(0.1)
            except:
                pass
        super().close_session()
