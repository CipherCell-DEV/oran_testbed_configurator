import time
from typing import override

from model.traffic.traffic_handler import TrafficServer, TrafficClient


class IPerfServer(TrafficServer):

    @override
    def start_server(self):
        pass

    @override
    def stop_server(self):
        pass


class IPerfClient(TrafficClient):

    @override
    def send_traffic(self, packet_size: int, timeout: int = 100) -> bool:
        """Run a iPerf3 client in the persistent session"""
        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        ping_cmd = self._cmd_prefix + f'iperf3 --client {self._server_address} --port {self._server_port}'
        # Maybe set --length (Buffer size)
        # --bind server_address
        # Interesting flags: --reverse, --bidir
        cmd = f'{ping_cmd}; echo "EXIT_CODE:$?"'

        try:
            self.process.stdin.write(cmd + '\n')
            self.process.stdin.flush()
            timeout_s = timeout / 1000 - 0.01

            start_time = time.time()
            while time.time() - start_time < timeout_s:
                import select
                ready, _, _ = select.select([self.process.stdout], [], [], timeout_s)
                if ready and (line := self.process.stdout.readline()):
                    line = line.strip()
                    if line.startswith("EXIT_CODE:"):
                        return int(line.split(":")[1]) == 0
                if self.process.poll() is not None:
                    print("Bash session terminated unexpectedly")
                    return False
            print("iPerf client timed out")
            return False
        except Exception as e:
            print(f"iPerf client failed: {e}")
            return False
