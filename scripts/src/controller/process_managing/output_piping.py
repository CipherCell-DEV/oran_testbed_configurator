import logging
import os
import re
from threading import Thread
from time import sleep

from process_managing.program_state_monitor import ProgramStateData
from utils import GENERAL_SUBPROCESS_TIMEOUT, get_operating_system, OperatingSystem
from utils_config import ProgramState

# want to remove color characters and docker "Enable Watch" console artefacts
ansi_escape = re.compile(r'\x1B(?:[0-9@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
docker_enable_watch = re.compile(r'w Enable Watch')


class OutputBuffer:
    def __init__(self, capacity : int):
        self._capacity :int = capacity
        self._buffer = [str] * self._capacity
        self._num_read_lines : int = 0 # number of lines that have been stored in the buffer over its lifetime

    def add_line(self, line : str):
        self._buffer[self._num_read_lines] = line



class OutputPipe:
    def __init__(self, data : ProgramStateData, log_location_path: str):
        self.program_state_data : ProgramStateData = data
        self.pipe_name : str = self.get_pipe_path(data.program.name) # temporary program output
        self.log_file_name : str = os.path.join(log_location_path, f"{data.program.name}.log") # permanent program output log
        self.pipe_created : bool = False

        # TODO: windows compatibility (mkfifo is not available, also check other program aspects not compatible with windows ...)
        if get_operating_system().value is OperatingSystem.WINDOWS.value:
            logging.error("Windows is currently not supported!")
            exit(1)

        try:
            # Delete old log file contents
            open(self.log_file_name, 'w').close()
            os.mkfifo(self.pipe_name)
            logging.debug(f"Named pipe created at: {self.pipe_name}")
            self.pipe_created = True
        except FileExistsError:
            logging.debug(f"Named pipe already exists at: {self.pipe_name}")
            self.pipe_created = True
        except OSError as e:
            logging.error(f"Error: {e}. Failed to create a named pipe for output processing")
            self.pipe_created = False

    @staticmethod
    def get_pipe_path(program_name : str) -> str:
        if get_operating_system().value is not OperatingSystem.WINDOWS.value:
            return os.path.join("/tmp", program_name)
        else:
            # TODO: Pipes are not supported on windows the way they are on unix. Look into win32pipe or win32file
            return os.path.abspath(os.path.join(os.sep, "tmp", program_name))


class OutputPipeListenerThread:
    def __init__(self, output_pipes : OutputPipe):
        self.output_pipes = output_pipes
        self.thread = None
        self.running = False

    def _pipe_thread_funct(self):
        with open(self.output_pipes.pipe_name, 'r') as pipe:
            logging.debug(f"Listening to pipe {self.output_pipes.pipe_name} ...")
            while self.running:
                for line in pipe:
                    if not self.running:
                        break
                    line = docker_enable_watch.sub('', ansi_escape.sub('', line))
                    if len(line.strip()) > 0:
                        with open(self.output_pipes.log_file_name, "a") as logfile:
                            logfile.write(f"{line}")
                            # Only if program is not running: -> check output for state transitions
                            if self.output_pipes.program_state_data.program_state.value != ProgramState.RUNNING.value:
                                self.output_pipes.program_state_data.change_state_on_output(line)
        logging.info(f"Ending Output Processing thread {self.output_pipes.pipe_name}")

    def start_thread(self):
        self.running = True
        self.thread = Thread(target=self._pipe_thread_funct)
        self.thread.start()
        logging.info(f"Started Output Processing thread {self.output_pipes.pipe_name}")


    def stop_thread(self):
        self.running = False
        self.thread.join(timeout=GENERAL_SUBPROCESS_TIMEOUT)