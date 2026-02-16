"""
ICMP ping-based traffic handler for bidirectional testing.

Uses standard ping command for generating ICMP traffic.
No receiver needed as ICMP echo replies are handled by the kernel.
"""

import time
from typing import override

from trafficker.traffic_handler.traffic_handler import TrafficReceiver, TrafficSender


# Maximum ICMP packet payload size (65,507 bytes theoretical max for IPv4)
# Keeping 65,000 as safe practical limit
MAX_PING_PACKET_SIZE = 65_000


class PingReceiver(TrafficReceiver):
    """
    Ping receiver (no-op implementation).

    ICMP echo replies are handled automatically by the kernel,
    so no explicit receiver process is needed.
    """

    @override
    def start_receiver(self) -> None:
        """No-op: ICMP replies handled by kernel."""
        pass

    @override
    def stop_receiver(self) -> None:
        """No-op: ICMP replies handled by kernel."""
        pass


class PingSender(TrafficSender):
    """Ping client for sending ICMP echo requests."""

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
        """
        Send ICMP ping packet.

        Args:
            packet_size: Payload size in bytes (clamped to 65,000 max)
            timeout: Timeout in milliseconds

        Returns:
            True if ping successful (received echo reply), False otherwise
        """
        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if packet_size > MAX_PING_PACKET_SIZE:
            print(f'Packet size cannot be bigger than {MAX_PING_PACKET_SIZE // 1000} kB! '
                  f'Reducing to {MAX_PING_PACKET_SIZE // 1000} kB.')
            packet_size = MAX_PING_PACKET_SIZE

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

                if self.process.poll() is not None:
                    print("Session terminated unexpectedly")
                    return False

            print(f"Ping timed out after {timeout}ms")
            return False

        except Exception as e:
            print(f"Ping failed: {e}")
            return False
