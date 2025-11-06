import os
import subprocess
import time
from abc import abstractmethod, ABC
from typing import override

from model.traffic.traffic_config import TrafficParameters


class TrafficHandler(ABC):

    def __init__(self, parameters: TrafficParameters, service_name: str, server_address: str, server_port: int = 5301):
        self._parameters = parameters
        self.__service_name = service_name
        self._server_address = server_address
        self._server_port = server_port

        self.process = None

    def _execute_cmd(self, cmd: str) -> None:
        # print(self.__service_name + ': ' + cmd.strip())
        if not cmd.endswith('\n'):
            cmd += '\n'
        self.process.stdin.write(cmd)
        self.process.stdin.flush()

    def start_session(self) -> None:
        """Start a persistent bash session in the UE container"""
        if self._parameters.use_nist:
            if self._parameters.nist_vm == 'local':
                cmd = ['bash']
            else:
                cmd = ['ssh', self._parameters.nist_vm]
        else:
            compose_files = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']
            compose_file_exists = any(os.path.isfile(os.path.join(self._parameters.workdir, f)) for f in compose_files)
            if not compose_file_exists:
                raise FileNotFoundError(f"No docker-compose file found in {self._parameters.workdir}")

            cmd = ['docker', 'compose', 'exec', '-T', self.__service_name, 'bash']

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._parameters.workdir
        )
        self.initialize_shell()

    def initialize_shell(self):
        self._execute_cmd('echo READY')
        if not self._wait_for_marker('READY'):
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

    def _copy_script_to_remote(self, file_name: str) -> str:
        script_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..',
                                   'patches', 'templates', 'traffic', file_name)
        script_path = os.path.abspath(script_path)

        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Template script not found: {script_path}")

        if self._parameters.nist_vm.startswith('root@'):
            target_dir = '/root'
        else:
            nist_vm = self._parameters.nist_vm
            target_dir = f'/home/{nist_vm.split("@")[-1] if "@" in nist_vm else nist_vm}'

        target_path = f'{target_dir}/{file_name}'

        try:
            scp_cmd = ['scp', script_path, f"{self._parameters.nist_vm}:{target_path}"]
            result = subprocess.run(scp_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"Failed to copy script to remote host: {result.stderr}")

        except Exception as e:
            raise RuntimeError(f"Error copying script to remote host: {e}")

        return target_path

    @property
    def _cmd_prefix(self) -> str:
        if self.__service_name.startswith('ue'):
            return (('sudo ' if self._parameters.use_nist else '') + 'ip netns exec '
                    + (self.__service_name if self._parameters.use_nist else 'ue1'))  # FIXME: Temporary workound
        else:
            return ''

    def _exec_and_wait_for_marker(self, cmd: str, marker: str, delay_before_check: float = 0.3,
                                  timeout: int = 2) -> bool:
        self._execute_cmd(cmd)
        time.sleep(delay_before_check)
        return self._wait_for_marker(marker, timeout)

    def _wait_for_marker(self, marker: str, timeout: int = 2) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            import select
            ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
            if ready:
                line = self.process.stdout.readline().strip()
                if line and marker in line:
                    return True
        return False


class TrafficReceiver(TrafficHandler, ABC):

    @override
    def __init__(self, parameters: TrafficParameters, service_name: str, server_address: str, server_port: int = 5301):
        super().__init__(parameters, service_name, server_address, server_port)
        self._server_running = False

    @abstractmethod
    def start_receiver(self) -> None:
        pass

    @abstractmethod
    def stop_receiver(self) -> None:
        pass


class TrafficSender(TrafficHandler, ABC):

    @abstractmethod
    def send_traffic(self, packet_size: int, timeout: int = 100) -> None:
        pass
