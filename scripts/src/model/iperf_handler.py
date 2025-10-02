import subprocess
import time


class IPerfHandler:

    def __init__(self, workdir: str, service_name: str, server_address: str, server_port: int = 5201):
        self.__service_name = service_name
        self.__workdir = workdir
        self._server_address = server_address
        self._server_port = server_port
        self.process = None

    def start_session(self) -> None:
        cmd = ['docker', 'compose', 'exec', '-T', self.__service_name, 'bash']
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.__workdir
        )
        self.initialize_shell()

    def initialize_shell(self):
        init_timeout = 2
        self.process.stdin.write('echo READY\n')
        self.process.stdin.flush()
        start_time = time.time()
        while time.time() - start_time < init_timeout:
            import select
            ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
            if ready:
                line = self.process.stdout.readline()
                if line and 'READY' in line:
                    break
        else:
            print('Initializing shell timed out')

    def close_session(self):
        """Close the persistent session"""
        if self.process:
            try:
                self.process.stdin.write('exit\n')
                self.process.stdin.flush()
                self.process.wait(timeout=2)
            except:
                self.process.terminate()
            finally:
                self.process = None
                print("Closed UE container session")

    @property
    def _cmd_prefix(self) -> str:
        if self.__service_name == 'ue1':
            return 'ip netns exec ue1'
        else:
            return ''

class IPerfServer(IPerfHandler):

    def run_server(self):
        pass

class IPerfClient(IPerfHandler):

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
