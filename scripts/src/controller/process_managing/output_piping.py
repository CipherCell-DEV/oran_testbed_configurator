import collections
import logging
import os
import re
import textwrap
import threading
from threading import Thread

from controller.process_managing.program_state_monitor import ProgramStateData
from controller.utils import GENERAL_SUBPROCESS_TIMEOUT, get_operating_system, OperatingSystem
from model.utils_config import ProgramState
from model.utils_config import MAX_DISPLAY_LINE_LENGTH

# want to remove color characters and docker "Enable Watch" console artefacts
ansi_escape = re.compile(r'\x1B(?:[0-9@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
docker_enable_watch = re.compile(r'w Enable Watch')


class OutputBuffer:
    """
    Buffer used to store the last few lines of the output of running programs.
    These lines are used by the Python Live Display to show the live program output.
    """
    def __init__(self, capacity : int):
        self._capacity :int = capacity
        self._buffer = collections.deque(maxlen = self._capacity)
        self._lock = threading.Lock()

    def add_line(self, line : str):
        with self._lock:
            wrapped_lines = textwrap.wrap(line.rstrip(), MAX_DISPLAY_LINE_LENGTH)
            self._buffer.extend(wrapped_lines)

    def get_combined_string(self) -> str:
        with self._lock:
            return f"{os.linesep}".join(self._buffer)


class OutputPipe:
    """
    This class manages the output of running programs.
    The output of all running programs is first piped into /tmp/<program name>.
    Afterward, all lines are read and processed.
    This class is used by the OutputPipeListenerThread
    """
    def __init__(self, data : ProgramStateData, log_location_path: str, buffer : OutputBuffer | None = None):
        self.program_state_data : ProgramStateData = data
        self.pipe_name : str = self.get_pipe_path(data.program.name) # temporary program output
        self.log_file_name : str = os.path.join(log_location_path, f"{data.program.name}.log") # permanent program output log
        self.pipe_created : bool = False
        self.buffer : OutputBuffer | None = buffer

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
    """
    Output Processing Thread. Analyzes all lines of program output.
    Line processing does the following:
    - Check if output line would trigger a state change and if so, initiate state change
    - Print output line into log file (under logs/run_logs/<program name>,
      may be different if you modified log paths in the config files)
    - If needed, store output line in a buffer (for e.g. for Python Live Display)
    """
    def __init__(self, output_pipes : OutputPipe):
        self.output_pipes = output_pipes
        self.thread = None
        self.running = False

    def _pipe_thread_funct(self):
        buffer_output = self.output_pipes.buffer is not None
        with os.fdopen(os.open(self.output_pipes.pipe_name, os.O_RDONLY | os.O_NONBLOCK), 'r') as pipe:
            logging.debug(f"Listening to pipe {self.output_pipes.pipe_name} ...")
            while self.running:
                for line in pipe:
                    if not self.running:
                        break
                    line = docker_enable_watch.sub('', ansi_escape.sub('', line))
                    if len(line.strip()) > 0:
                        with open(self.output_pipes.log_file_name, "a") as logfile:
                            logfile.write(f"{line}")
                            if buffer_output:
                                self.output_pipes.buffer.add_line(line)
                            # Only if program is not running: -> check output for state transitions
                            if self.output_pipes.program_state_data.program_state.value != ProgramState.RUNNING.value:
                                self.output_pipes.program_state_data.change_state_on_output(line)
        logging.debug(f"Ending Output Processing thread {self.output_pipes.pipe_name}")

    def start_thread(self):
        self.running = True
        self.thread = Thread(target=self._pipe_thread_funct)
        self.thread.start()
        logging.debug(f"Started Output Processing thread {self.output_pipes.pipe_name}")


    def stop_thread(self):
        self.running = False
        self.thread.join(timeout=GENERAL_SUBPROCESS_TIMEOUT)