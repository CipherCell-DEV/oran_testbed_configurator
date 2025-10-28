import logging

from abc import ABC
from threading import Thread
from typing import List

from controller.demo_runner import DemoRunner
from controller.process_managing.output_piping import OutputPipeListenerThread
from controller.process_managing.program_state_monitor import ProgramRecord, ProgramStateData
from controller.utils import GENERAL_SUBPROCESS_TIMEOUT
from model.utils_config import ProgramState

CHECKUP_PERIOD = 2


class ProcessManager(ABC):
    def __init__(self, runner: DemoRunner):
        self.demo_runner = runner
        self._setup_completed: bool = False
        self._program_record: ProgramRecord = ProgramRecord()
        self._program_state_data: List[ProgramStateData] = []

        # Loop condition for internal threads
        self._stop_watchdogs: bool = False

        # Threads
        self._state_checkers : List[Thread] = []
        self._output_listener_threads: List[OutputPipeListenerThread] = []
        self._record_checker: Thread = Thread() # Thread that prints the names of all successfully started programs. Purely informational.

    def _handle_restart(self, *args):
        raise NotImplementedError("Base class does not implement _handle_restart!")

    def _state_checker_thread_func(self, state : ProgramStateData, *args):
        """
        Monitor state changes until RUNNING state is reached.
        Restarts programs if they time out
        """
        while not self._stop_watchdogs:
            with state.cv_state_change:
                if state.cv_state_change.wait(state.program.timeout):
                    logging.debug(f"State change: {state.program.name} -> {state.program_state.name}")
                    if state.program_state.value == ProgramState.RUNNING.value:
                        logging.info(f"Program {state.program.name} started running. Will stop timeout watcher.")
                        break
                else:
                    # My state has not changed during my timeout period
                    # If my preconditions are already running, but I do not, then I will trigger a restart:
                    if state.program_state.value is not ProgramState.RUNNING.value:
                        if state.are_preconditions_met():
                            logging.info(f"Timeout detected: {state.program.name}.")
                            if state.cur_num_restarts >= state.program_num_restarts:
                                logging.error(f"Reached max. amount of restarts for program {state.program.name}.")
                            else:
                                logging.info(f"Restarting program {state.program.name}.")
                                # manager dependent restart implementation
                                success = self._handle_restart(*args)
                                if not success:
                                    logging.error(f"Failed to restart program {state.program.name}!")
        logging.debug(f"State checker {state.program.name} ended.")

    def _record_checker_thread_func(self):
        """
        The program record contains the names of all programs which have started successfully (i.e. reached program state RUNNING).
        Each change of  the program record alerts the condition variable cv_finished_programs.
        This function perpetually waits for changes in the program record and upon change prints debug information.
        TODO: The record checker thread is used for debugging purposes only, maybe remove it later on for better performance.
        """
        while not self._stop_watchdogs:
            with self._program_record.cv_finished_programs:
                if self._program_record.cv_finished_programs.wait(GENERAL_SUBPROCESS_TIMEOUT):
                    self._program_record.log_finished_programs()
        logging.info(f"Record checker thread ended.")


    def setup_program_data(self):
        raise NotImplementedError("Base class does not implement setup_program_data")

    def start_programs(self):
        """
        Start thread, which prints the name of each process having reached state RUNNING.
        """
        self._record_checker = Thread(target=self._record_checker_thread_func)
        self._record_checker.start()

    def get_view_ref_str(self, **kwargs) -> List[str]:
        raise NotImplementedError("Base class does not implement get_view_ref_str")

    def cleanup_and_shutdown(self):
        # ending watchdog threads
        logging.info("Stopping watchdogs ...")
        self._stop_watchdogs = True
        # Notify all watchdog threads such that they can exit their while !_stop_watchdog loops
        logging.info("Notify all watchdog condition variables")
        with self._program_record.cv_finished_programs:
            self._program_record.cv_finished_programs.notify_all()
        for state_machine in self._program_state_data:
            with state_machine.cv_state_change:
                state_machine.cv_state_change.notify_all()
        # Join threads
        logging.info("Waiting for all watchdog processes to close...")
        self._record_checker.join(GENERAL_SUBPROCESS_TIMEOUT)
        if self._record_checker.is_alive():
            logging.error(f"Failed to stop program record checker thread!")
        for thread in self._state_checkers:
            thread.join(GENERAL_SUBPROCESS_TIMEOUT)
            if thread.is_alive():
                logging.error(f"Failed to stop state checker thread {thread.name}!")
        # Stop Logging threads
        logging.info("Stopping logging threads ...")
        for thread in self._output_listener_threads:
            thread.stop_thread()
