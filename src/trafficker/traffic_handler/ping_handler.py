import time
from typing import override

from trafficker.traffic_handler.traffic_handler import TrafficReceiver, TrafficSender


class PingReceiver(TrafficReceiver):
    """Ping server that does nothing - no server needed for ping"""

    @override
    def start_receiver(self) -> None:
        pass

    @override
    def stop_receiver(self) -> None:
        pass


class PingSender(TrafficSender):
    """Ping client that sends ICMP packets"""

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
        """Run a ping command in the persistent session"""
        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if packet_size > 65000:
            print('Packet size cannot be bigger than 65 kB! Reducing it to 65 kB.')
            packet_size = 65000

        ping_cmd = f'{self._cmd_prefix} ping -s {packet_size} -c 1 {self._server_address}'
        cmd = f'{ping_cmd}; echo "EXIT_CODE:$?"'
        print(ping_cmd)

        try:
            self._execute_cmd(cmd)
            timeout_s = timeout / 1000.0 - 0.01

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
                                print(f"Ping failed with exit code {exit_code}")
                            return success

                # Check if process is still alive
                if self.process.poll() is not None:
                    print("Session terminated unexpectedly")
                    return False

            print(f"Ping timed out after {timeout}ms")
            return False

        except Exception as e:
            print(f"Ping failed: {e}")
            return False
