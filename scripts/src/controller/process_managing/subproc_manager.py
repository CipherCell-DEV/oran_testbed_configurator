import logging
import subprocess
from threading import Thread
from pathlib import Path
from typing import List

from controller.demo_runner import DemoRunner
from controller.process_managing.process_manager_base import ProcessManager, GENERAL_SUBPROCESS_TIMEOUT, CHECKUP_PERIOD
from controller.process_managing.output_piping import OutputPipe, OutputPipeListenerThread, OutputBuffer
from controller.process_managing.program_state_monitor import ProgramStateData, ProgramRecord
from model.utils_config import ProgramState


class SubProcRunnerThread:
    def __init__(self, state : ProgramStateData, record : ProgramRecord):
        self.program_state : ProgramStateData = state
        self._record : ProgramRecord = record
        self.program_thread : Thread = Thread()
        self.running = False
        self._process: subprocess.Popen | None = None

    def _runner_thread_funct(self):
        while self.running:
            if not self.program_state.are_preconditions_met():
                with self._record.cv_finished_programs:
                    self._record.cv_finished_programs.wait(GENERAL_SUBPROCESS_TIMEOUT)
                    if not self.program_state.are_preconditions_met():
                        continue
            # can now start program as subprocess
            logging.debug(f"Start Program {self.program_state.program.name}")
            with open(OutputPipe.get_pipe_path(self.program_state.program.name), "w") as pipe:
                self._process = subprocess.Popen(
                    self.program_state.program.command,
                    # send output to monitored pipe
                    stdout=pipe,
                    stderr=subprocess.STDOUT,  # redirect stderr into stdout
                    text=True,  # decode bytes -> str
                    bufsize=1,  # line-buffered output
                    universal_newlines=True,  # ensure consistent line endings
                    cwd=self.program_state.program.working_directory  # set working directory
                )

            if not self.program_state.use_state_checking:
                # Since this program has no state transitions, we immediately consider it running
                self._record.add_finished_program(self.program_state.program.name)
                self.program_state.program_state = ProgramState.RUNNING

            logging.debug(f"Program: {self.program_state.program.name} started")
            break
        logging.debug(f"Ending Program Starter thread {self.program_state.program.name}.")

    def get_process(self):
        return self._process

    def start_thread(self):
        self.running = True
        self.program_thread = Thread(target=self._runner_thread_funct)
        self.program_thread.start()
        logging.debug(f"Program starter thread for {self.program_state.program.name} started")

    def set_stop_signal(self):
        self.running = False

    def join_thread(self):
        self.program_thread.join(timeout=GENERAL_SUBPROCESS_TIMEOUT)


class SubprocessManager(ProcessManager):
    def __init__(self, runner : DemoRunner):
        super().__init__(runner)
        # Threads
        self._program_starter_threads: List[SubProcRunnerThread] = [] # List elements contain references to running subprocesses
        # Buffer used by view
        self._output_buffers : dict[str : OutputBuffer] = {}

    # region internal_subprocess_setup
    def _validate(self) -> bool:
        if CHECKUP_PERIOD <= 0 or GENERAL_SUBPROCESS_TIMEOUT < 0:
            logging.error("Invalid program constants")
            return False
        return True
    # endregion

    # region private_override
    def _handle_restart(self, *args) -> bool:
        # expect (self, SubProcRunnerThread)
        if len(args) < 1:
            logging.error(f"Invalid number of arguments for restart handler function! ({len(args)})")
            return False
        if not isinstance(args[0], SubProcRunnerThread):
            logging.error("Invalid parameter for restart handler function!")
            return False
        thread_data : SubProcRunnerThread = args[0]
        process_state = thread_data.program_state
        if thread_data.get_process() is not None:
            thread_data.get_process().kill()
            process_state.cur_num_restarts = process_state.cur_num_restarts + 1
            try:
                thread_data.get_process().wait(GENERAL_SUBPROCESS_TIMEOUT)
            except subprocess.TimeoutExpired:
                logging.error(f"Program restart of {process_state.program.name} has timed out!")
                return False
            # restart process
            logging.info(f"Program {process_state.program.name} has stopped. Restarting ...")
            process_state.change_state_to(ProgramState.STOPPED)
            with open(OutputPipe.get_pipe_path(process_state.program.name), "w") as pipe:
                self._process = subprocess.Popen(
                    process_state.program.command,
                    # send output to monitored pipe
                    stdout=pipe,
                    stderr=subprocess.STDOUT,  # redirect stderr into stdout
                    text=True,  # decode bytes -> str
                    bufsize=1,  # line-buffered output
                    universal_newlines=True,  # ensure consistent line endings
                    cwd=process_state.program.working_directory  # set working directory
                )
            return True
        logging.error("No process to restart ...")
        logging.debug("Process may not be running because starter thread is stuck. Are preconditions met? Might also be a deadlock ...")
        return False
    # endregion

    def cleanup_and_shutdown(self):
        """Stop all Docker containers using docker compose down (If running using docker)"""
        working_dir = self.demo_runner.cfg.environment.build_dir

        try:
            logging.info("Stopping all Docker containers...")
            result = subprocess.run(
                ["docker", "compose", "down"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logging.info("All containers stopped successfully.")
            else:
                logging.warning(f"Docker compose down returned non-zero exit code: {result.returncode}")
                logging.warning(f"stderr: {result.stderr}")
        except subprocess.TimeoutExpired:
            logging.error("Timeout while stopping containers. Forcing container termination...")
            subprocess.run(["docker", "compose", "kill"], cwd=working_dir, capture_output=True)
        except Exception as e:
            logging.error(f"Error stopping containers: {e}")

        # stop reading from program output and state transition processing
        super().cleanup_and_shutdown()

        # Stop program runner threads which may still be running
        # First set bool for outer loop
        logging.info(f"Stopping program starters...")
        for thread in self._program_starter_threads:
            thread.set_stop_signal()
        # notify cv to escape inner loop
        with self._program_record.cv_finished_programs:
            self._program_record.cv_finished_programs.notify_all()
        # join all programs
        for thread in self._program_starter_threads:
            thread.join_thread()

        # stop all processes spawned by the starter threads
        for thread in self._program_starter_threads:
            if thread.get_process() is not None:
                thread.get_process().kill()
                try:
                    val = thread.get_process().wait(GENERAL_SUBPROCESS_TIMEOUT)
                    logging.debug(f"Proces kill result: {val}")
                except subprocess.TimeoutExpired:
                    logging.error(f"Failed to stop spawned subprocess for {thread.program_state.program.name}")


    def setup_program_data(self):
        # create log directory
        if not self._setup_completed:
            Path(self.demo_runner.cfg.programs.log_dir).mkdir(parents=True, exist_ok=True)
            for to_run in self.demo_runner.programs:
                # Assemble general program data and associated program state
                new_state_obj = ProgramStateData(to_run, to_run.timeout, to_run.max_num_restarts, self._program_record)
                self._program_state_data.append(new_state_obj)
                # Use program data and state to start a thread, which itself starts a process and stores the reference to the process
                new_subprocess_proc_obj = SubProcRunnerThread(new_state_obj, self._program_record)
                # The view layer wants to display the latest process output. Create buffer to be used by view
                self._output_buffers[to_run.name] = OutputBuffer(self.demo_runner.cfg.programs.show_num_lines)
                self._program_starter_threads.append(new_subprocess_proc_obj)
            self._setup_completed = True
        else:
            logging.warning("Subprocess manager is already set up!")


    def start_programs(self):
        super().start_programs()
        for program_nr in range(len(self._program_starter_threads)):
            cur_program = self._program_starter_threads[program_nr]
            # create thread, which parses all program output lines
            # we buffer the output such that a  view can access and render them
            output_piping = OutputPipe(cur_program.program_state, self.demo_runner.cfg.programs.log_dir,
                                       self._output_buffers[cur_program.program_state.program.name])
            output_processing = OutputPipeListenerThread(output_piping)
            self._output_listener_threads.append(output_processing)
            output_processing.start_thread()

            # start a thread which checks all state changes
            state_check = Thread(target=self._state_checker_thread_func,
                                 args=[cur_program.program_state, cur_program])
            state_check.start()
            self._state_checkers.append(state_check)

            # execute command inside thread
            cur_program.start_thread()

        logging.debug("All programs are scheduled to start!")


    def get_view_ref_str(self, **kwargs) -> List[str]:
        for k, val in kwargs.items():
            if k == "name":
                return [self._output_buffers[val].get_combined_string()]
        return [""]

