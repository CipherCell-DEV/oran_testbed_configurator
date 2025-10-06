import subprocess
from typing import List, Optional

from controller.program_state_monitor import ProgramStateMonitor, ProgramState
from model.setup_configuration import SetupConfiguration
from model.utils_config import ProgramType

RESTART_TIMEOUT_RIC_IN_S = 30
RESTART_TIMEOUT_CORE_IN_S = 30
RESTART_TIMEOUT_GNB_IN_S = 30
RESTART_TIMEOUT_UE_IN_S = 30


class Program:
    """
    Represents a wrapper around a system process that can be started,
    monitored, and waited on. Each Program instance corresponds to a
    single external command with its own working directory.
    """

    def __init__(self, name: str, command: List[str], working_dir: str, program_type: ProgramType,
                 setup_cfg: SetupConfiguration,
                 enable_program_state_checker: Optional[bool] = False):
        """
        Initialize a Program instance.

        @param name        A human-readable identifier for the program.
        @param command     The command to execute, as a list of arguments
                           (e.g., ["python3", "app.py"]).
        @param working_dir The directory in which the command will be run.
        """
        self._reader_thread = None
        self._reader_running = None
        self.name = name
        self.command = command
        self.process: subprocess.Popen | None = None
        self.working_dir: str = working_dir

        restart_timeout = 0
        if program_type == ProgramType.RIC:
            restart_timeout = RESTART_TIMEOUT_RIC_IN_S
        elif program_type == ProgramType.CORE:
            restart_timeout = RESTART_TIMEOUT_CORE_IN_S
        elif program_type == ProgramType.GNB:
            restart_timeout = RESTART_TIMEOUT_GNB_IN_S
        elif program_type == ProgramType.UE:
            restart_timeout = RESTART_TIMEOUT_UE_IN_S

        self._program_state_checker: ProgramStateMonitor = \
            (ProgramStateMonitor(program_type=program_type,
                                 setup_config=setup_cfg,
                                 restart_timeout_in_s=restart_timeout) if enable_program_state_checker else None)

    def get_current_state(self) -> ProgramState:
        if self._program_state_checker:
            return self._program_state_checker.get_current_state()
        else:
            return ProgramState.UNDEFINED

    def get_program_state_checker(self):
        return self._program_state_checker

    def start(self):
        """
        Start the program as a subprocess.

        - Redirects both stdout and stderr into a single stream.
        - Uses line-buffered text mode for real-time output capture.
        - Runs the process in the specified working directory.
        """
        self.process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,  # capture standard output
            stderr=subprocess.STDOUT,  # redirect stderr into stdout
            text=True,  # decode bytes -> str
            bufsize=1,  # line-buffered output
            universal_newlines=True,  # ensure consistent line endings
            cwd=self.working_dir  # set working directory
        )

        if self._program_state_checker:
            self._program_state_checker.start_watchdog_thread()

    def get_process(self) -> subprocess.Popen:
        """
        Get the underlying subprocess object.

        @return The subprocess.Popen instance created by start().
        """
        return self.process

    def get_process_name(self) -> str:
        """
        Get the program's human-readable name.

        @return The name string given at initialization.
        """
        return self.name

    def wait_process(self):
        """
        Block until the process has finished execution.

        If the process is running, this will wait until it exits.
        """
        if self.process:
            self.process.wait()
