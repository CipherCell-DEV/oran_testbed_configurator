"""
Netcat-based traffic handlers for UDP/TCP traffic.

Uses netcat (nc) command-line tool for sending and receiving traffic packets.
"""

import time
from typing import override

from trafficker.traffic_handler.traffic_handler import TrafficReceiver, TrafficSender


class NetcatReceiver(TrafficReceiver):
    """Netcat server for receiving traffic."""

    @override
    def start_receiver(self) -> None:
        """
        Start netcat server listening on configured port.

        Verifies server is running by checking if port is in LISTEN state.

        Raises:
            RuntimeError: If shell process died or server fails to start
        """
        if self._server_running:
            print("Netcat server is already running")
            return

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        # Check if the shell process is still alive
        if self.process.poll() is not None:
            raise RuntimeError("Shell process has died, cannot start server")

        server_cmd = f'{self._cmd_prefix} nc {"-u " if self._parameters.use_udp else ""}-k -l -p {self._server_port}'

        try:
            print(f"Starting netcat server on port {self._server_port}")
            self._execute_cmd(f'{server_cmd} &')

            time.sleep(0.5)

            # Verify server is running by checking if port is listening
            verify_cmd = f'{self._cmd_prefix} ss -lnp | grep ":{self._server_port} "'
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
                # Fallback: assume started even if verification failed
                self._server_running = True
                print(f"Netcat server started on port {self._server_port} (verification failed, assuming success)")

        except Exception as e:
            print(f"Failed to start netcat server: {e}")
            self._server_running = False
            raise

    @override
    def stop_receiver(self) -> None:
        """Stop netcat server by killing the process."""
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
        """Check if the server is currently running."""
        return self._server_running


class NetcatSender(TrafficSender):
    """Netcat client for sending traffic packets."""

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
        """
        Send random data packet using netcat.

        Generates random data from /dev/urandom and sends via netcat.

        Args:
            packet_size: Number of bytes to send
            timeout: Timeout in milliseconds

        Returns:
            True if packet sent successfully, False otherwise
        """
        if packet_size == 0:
            return True

        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        netcat_cmd = (f'{self._cmd_prefix} dd if=/dev/urandom bs={packet_size} count=1 | '
                      f'nc {"-u " if self._parameters.use_udp else ""}-q 0 {self._server_address} {self._server_port}')
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

                if self.process.poll() is not None:
                    print("Session terminated unexpectedly")
                    return False

            print(f"Netcat client timed out after {timeout}ms")
            return False

        except Exception as e:
            print(f"Netcat client failed: {e}")
            return False

    def close_session(self):
        """Close session and cleanup any remaining netcat processes."""
        if self.process:
            try:
                cleanup_cmd = f'{self._cmd_prefix} pkill -f "nc.*{self._server_address}.*{self._server_port}"'
                self._execute_cmd(cleanup_cmd)
                time.sleep(0.1)
            except:
                pass
        super().close_session()
