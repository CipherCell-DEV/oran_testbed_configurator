import subprocess
import time


class UEContainer:
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.process = None

    def start_session(self):
        """Start a persistent bash session in the UE container"""
        cmd = ['docker', 'compose', 'exec', '-T', 'ue1', 'bash']
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.workdir
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

    def run_ping(self, destination: str, packet_size: int, timeout: int):
        """Run a ping command in the persistent session"""
        if not self.process:
            raise RuntimeError("No active session. Call start_session() first.")

        if packet_size > 60000:
            print('Packet size currently cannot be more than 60 kB! Reducing it to 60 kB.')
            packet_size = 60000

        ping_cmd = f'ip netns exec ue1 ping -s {packet_size} -c 1 {destination}'
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
            print("Ping timed out")
            return False
        except Exception as e:
            print(f"Ping failed: {e}")
            return False

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
