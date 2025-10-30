import subprocess
import time
from abc import abstractmethod, ABC
import os


class TrafficHandler(ABC):

    def __init__(self, workdir: str, service_name: str, server_address: str, server_port: int = 5201,
                 use_nist: bool = False):
        self.__service_name = service_name
        self.__workdir = workdir
        self._server_address = server_address
        self._server_port = server_port
        self._use_nist = use_nist
        self.process = None

    def _execute_cmd(self, cmd: str) -> None:
        # print(self.__service_name, ':', cmd)
        if not cmd.endswith('\n'):
            cmd += '\n'
        self.process.stdin.write(cmd)
        self.process.stdin.flush()

    def start_session(self) -> None:
        """Start a persistent bash session in the UE container"""

        compose_files = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']
        compose_file_exists = any(os.path.isfile(os.path.join(self.__workdir, f)) for f in compose_files)
        if not compose_file_exists:
            raise FileNotFoundError(f"No docker-compose file found in {self.__workdir}")

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
        self._execute_cmd('echo READY')
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
                self._execute_cmd('exit')
                self.process.wait(timeout=2)
            except:
                self.process.terminate()
            finally:
                self.process = None
                print("Closed container session")

    @property
    def _cmd_prefix(self) -> str:
        if self.__service_name.startswith('ue'):
            return 'ip netns exec ue1'  # + self.__service_name TODO
        else:
            return ''


class TrafficServer(TrafficHandler, ABC):

    @abstractmethod
    def start_server(self) -> None:
        pass

    @abstractmethod
    def stop_server(self) -> None:
        pass


class TrafficClient(TrafficHandler, ABC):

    @abstractmethod
    def send_traffic(self, packet_size: int, timeout: int = 100) -> None:
        pass
