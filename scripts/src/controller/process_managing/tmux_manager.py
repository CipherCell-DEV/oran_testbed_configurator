import logging
import os
import re
import subprocess
import time
from pathlib import Path
from threading import Thread
from time import sleep
from typing import List

import libtmux
from libtmux import Session, Pane

from controller.demo_runner import DemoRunner
from controller.process_managing.process_manager_base import ProcessManager, GENERAL_SUBPROCESS_TIMEOUT, CHECKUP_PERIOD
from process_managing.program_state_monitor import ProgramRecord, ProgramStateData
from utils_config import ProgramState

# want to remove color characters and docker "Enable Watch" console artefacts
ansi_escape = re.compile(r'\x1B(?:[0-9@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
docker_enable_watch = re.compile(r'w Enable Watch')

class OutputPipe:
    def __init__(self, data : ProgramStateData, log_location_path: str):
        self.program_state_data : ProgramStateData = data
        self.pipe_name : str = f"/tmp/{data.program.name}"
        self.log_file_name : str = os.path.join(log_location_path, f"{data.program.name}.log")
        self.pipe_created : bool = False

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
            logging.error(f"Error: {e}. Failed to create a named pipe for output processing (IPC tmux <-> python script)")
            self.pipe_created = False


class OutputPipeListenerThread:
    def __init__(self, output_pipes : OutputPipe):
        self.output_pipes = output_pipes
        self.thread = None
        self.running = False

    def _pipe_thread_funct(self):
        with open(self.output_pipes.pipe_name, 'r') as pipe:
            logging.info(f"Listening to pipe {self.output_pipes.pipe_name} ...")
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


class ProgramRunnerThread:
    def __init__(self, state : ProgramStateData, record : ProgramRecord, tmux_pane : Pane):
        self._program_state : ProgramStateData = state
        self._record : ProgramRecord = record
        self._pane = tmux_pane
        self.program_thread : Thread = Thread()
        self.running = False

    def _runner_thread_funct(self):
        while self.running:
            if not self._program_state.are_preconditions_met():
                with self._record.cv_finished_programs:
                    self._record.cv_finished_programs.wait(GENERAL_SUBPROCESS_TIMEOUT)
                    if not self._program_state.are_preconditions_met():
                        continue
            # can now start program
            logging.info(f"Start Program {self._program_state.program.name}")
            self._pane.send_keys(" ".join(self._program_state.program.command))
            if not self._program_state.use_state_checking:
                # Since this program has no state transitions, we immediately consider it running
                self._record.add_finished_program(self._program_state.program.name)
                self._program_state.program_state = ProgramState.RUNNING

            logging.info(f"Program: {self._program_state.program.name} started")
            break
        logging.info(f"Ending Program Starter thread {self._program_state.program.name}.")

    def start_thread(self):
        self.running = True
        self.program_thread = Thread(target=self._runner_thread_funct)
        self.program_thread.start()
        logging.info(f"Program starter thread for {self._program_state.program.name} started")


    def set_stop_signal(self):
        self.running = False

    def join_thread(self):
        self.program_thread.join(timeout=GENERAL_SUBPROCESS_TIMEOUT)


class TmuxManager(ProcessManager):
    def __init__(self, runner : DemoRunner):
        super().__init__(runner)
        # Tmux objects
        self._server = libtmux.Server()
        self._sessions: List[Session] = []
        self._session_prefix = runner.cfg.programs.session_prefix
        self._panes_per_session = runner.cfg.programs.panes_per_session

        # Which program state is associated with which pane?
        self._pane_state_pair : dict[str : ProgramStateData] = {}

        # Runnable Programs
        self._program_record : ProgramRecord = ProgramRecord()
        self._program_state_data: List[ProgramStateData] = []

        # Threads
        self._state_checkers : List[Thread] = []
        self._record_checker: Thread = Thread()
        self._output_listener_threads: List[OutputPipeListenerThread] = []
        self._program_starter_threads: List[ProgramRunnerThread] = []

        # Loop condition for threads
        self._stop_watchdogs : bool = False
        self._setup_completed : bool = False


    # region internal_helper
    @staticmethod
    def _is_tmux_installed() -> bool:
        result = subprocess.run(["tmux", "-V"],
                                timeout=GENERAL_SUBPROCESS_TIMEOUT,
                                text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        # Expected output is e.g.: tmux 3.2a
        return re.search("^tmux ", result.stdout) is not None


    def _get_session_index(self, name : str) -> int:
        """
        A negative return value indicates that no index has been found.
        """
        for index in range(len(self._sessions)):
            if self._sessions[index].name == name:
                return index
        return -1


    def _compute_num_sessions(self) -> int:
        needed_sessions = len(self._program_state_data) // self._panes_per_session
        if len(self._program_state_data) % self._panes_per_session != 0:
            needed_sessions = needed_sessions + 1
        return needed_sessions
    # endregion


    # region internal_tmux_setup
    def _generate_detached_sessions(self, force: bool = False) -> bool:
        """
        Creates new detached sessions for the programs. Since the number of programs
        shown per windows is limited, several sessions are created to accommodate all of them.
        If the force flag is not set, this function will fail if the sessions already exist.
        If the force flag is set, existing sessions with the same name will be destroyed and
        new sessions will be generated.
        :param force: Optional. If true, any existing session with the given name will be destroyed.
        :return: Success indication of newly created session
        """
        if not self._validate() :
            logging.error("Invalid session settings!")
            return False

        num_sessions = self._compute_num_sessions()
        if num_sessions == 0:
            logging.warning("No sessions to create! No programs are defined")
            return True
        else:
            for i in range(num_sessions):
                next_session_name = f"{self._session_prefix}{i}"
                if self._server.has_session(next_session_name):
                    if force:
                        logging.warning(f"Will destroy existing session: {next_session_name}")
                        self._server.kill_session(next_session_name)
                        logging.info(f"Session {next_session_name} has been destroyed")
                    else:
                        logging.error(f"Session {next_session_name} already exists! Cannot create session!")
                        return False
                logging.info(f"Create session: {next_session_name}")
                self._sessions.append(self._server.new_session(next_session_name))
        return True


    def _create_panes(self):
        for session in self._sessions:
            for i in range(self._panes_per_session - 1):
                session.active_pane.split()
            session.active_window.select_layout("tiled")


    def _validate(self) -> bool:
        if self._session_prefix is None or self._session_prefix == "":
            logging.error("Invalid session_prefix")
            return False
        if self._panes_per_session <= 0:
            logging.error("Invalid number of panes per window")
            return False
        if CHECKUP_PERIOD <= 0 or GENERAL_SUBPROCESS_TIMEOUT < 0:
            logging.error("Invalid program constants")
        return True
    # endregion


    # region thread_functions
    def _state_checker_thread_func(self, state : ProgramStateData):
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
                                for paneid in self._pane_state_pair:
                                    if self._pane_state_pair[paneid].program.name == state.program.name:
                                        # send command to this pane to end
                                        # paneid string has the following structure [sess_name]:[window_nr].[pane_nr]
                                        # we are interested in session name and pane nr
                                        sess_nr = self._get_session_index(paneid.split(":")[0])
                                        if sess_nr < 0:
                                            logging.fatal(f"Invalid session name for program {state.program.name} detected!")
                                            continue
                                        pane_nr = int(paneid.split(".")[-1])
                                        program_pane = self._sessions[sess_nr].panes[pane_nr]
                                        program_pane.send_keys("C-c")
                                        state.cur_num_restarts = state.cur_num_restarts + 1
                                        # Wait until program is stopped
                                        seconds_waited = 0
                                        while seconds_waited < GENERAL_SUBPROCESS_TIMEOUT:
                                            idle_command = os.path.basename(self._server.show_environment()['SHELL'])
                                            if program_pane.pane_current_command == idle_command:
                                                logging.info(f"Program {state.program.name} has stopped. Restarting ...")
                                                state.change_state_to(ProgramState.STOPPED)
                                                program_pane.send_keys(" ".join(state.program.command))
                                                break
                                            sleep(CHECKUP_PERIOD)
                                            seconds_waited = seconds_waited + CHECKUP_PERIOD


        logging.debug(f"State checker {state.program.name} ended.")


    def _record_checker_thread_func(self):
        while not self._stop_watchdogs:
            with self._program_record.cv_finished_programs:
                if self._program_record.cv_finished_programs.wait(GENERAL_SUBPROCESS_TIMEOUT):
                    self._program_record.log_finished_programs()
        logging.info(f"Record checker thread ended.")
    # endregion


    # region public_override
    def cleanup_and_shutdown(self):
        """Stop and kill all sessions"""
        for session in self._sessions:
            for pane in session.panes:
                pane.send_keys("C-c")
        logging.info("Waiting for all processes to close. This may take a while.")
        # after we send sigint to our programs, we wait until they and only the default shell command is running in tmux
        idle_command = os.path.basename(self._server.show_environment()['SHELL'])
        waited_seconds = 0
        while waited_seconds < GENERAL_SUBPROCESS_TIMEOUT:
            if len(self._sessions) == 0:
                logging.info("Sessions successfully closed!")
                waited_seconds = GENERAL_SUBPROCESS_TIMEOUT
                continue
            for session in self._sessions:
                all_session_panes_finished = True
                for pane in session.panes:
                    # we detect a finished command by checking the current running command
                    # if it is just the default shell, we assume nothing important is going on anymore
                    all_session_panes_finished = all_session_panes_finished and pane.pane_current_command == idle_command
                if all_session_panes_finished:
                    # we can kill this session
                    logging.info(f"Killing session {session.session_name}. Number of sessions remaining: {len(self._sessions) - 1}")
                    session.kill()
                    self._sessions.remove(session)
            # Programs are still running, check again later
            time.sleep(CHECKUP_PERIOD)
            waited_seconds += CHECKUP_PERIOD

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
        for thread in self._state_checkers:
            thread.join(GENERAL_SUBPROCESS_TIMEOUT)
        # Stop Logging threads
        logging.info("Stopping logging threads ...")
        for thread in self._output_listener_threads:
            thread.stop_thread()
        # Stop program runner threads which may still be running
        # First set bool for outer loop
        for thread in self._program_starter_threads:
            thread.set_stop_signal()
        # notify cv to escape inner loop
        with self._program_record.cv_finished_programs:
            self._program_record.cv_finished_programs.notify_all()
        # join all programs
        for thread in self._program_starter_threads:
            thread.join_thread()


    def setup_program_data(self):
        # create log directory
        if not self._setup_completed:
            Path(self.demo_runner.cfg.programs.log_dir).mkdir(parents=True, exist_ok=True)
            if not self._is_tmux_installed():
                logging.error("Tmux not installed")
                exit(1)
            for to_run in self.demo_runner.programs:
                new_state_obj = ProgramStateData(to_run, to_run.timeout, to_run.max_num_restarts, self._program_record)
                self._program_state_data.append(new_state_obj)
            if not self._generate_detached_sessions(True):
                logging.error("Failed to create tmux sessions!")
                self.cleanup_and_shutdown()
                exit(1)
            self._create_panes()
            self._setup_completed = True
        else:
            logging.warning("Tmux Manager was already set up!")


    def start_programs(self):
        self._record_checker = Thread(target=self._record_checker_thread_func)
        self._record_checker.start()
        for program_nr in range(len(self._program_state_data)):
            cur_program = self._program_state_data[program_nr]
            session_nr = program_nr // self._panes_per_session
            pane_nr = program_nr % self._panes_per_session
            if (session_nr >= len(self._sessions)) or (pane_nr >= len(self._sessions[session_nr].panes)):
                logging.error(f"Cannot open program in session pane: session: {session_nr}, pane: {pane_nr}")
            else:
                # start a thread which checks all state changes
                state_check = Thread(target=self._state_checker_thread_func, args=[cur_program])
                state_check.start()
                self._state_checkers.append(state_check)

                # get tmux addressing data
                program_pane = self._sessions[session_nr].panes[pane_nr]
                pane_id_str = f"{program_pane.session_name}:{program_pane.window_index}.{program_pane.pane_index}"

                # store relation: program + state data <-> pane in which it is running
                # we need panes later, as they handle the I/O of the program running in it
                self._pane_state_pair[pane_id_str] = cur_program

                # create thread, which parses all program output lines
                output_piping = OutputPipe(cur_program, self.demo_runner.cfg.programs.log_dir)
                output_processing = OutputPipeListenerThread(output_piping)
                self._output_listener_threads.append(output_processing)
                output_processing.start_thread()

                # instruct tmux to pipe its output to the pipe
                program_pane.send_keys(f"tmux pipe-pane -t {pane_id_str} 'cat > {output_piping.pipe_name}'")
                # change working directory:
                program_pane.send_keys(f"cd {cur_program.program.working_directory}")

                # execute command inside thread
                starter_thread = ProgramRunnerThread(cur_program, self._program_record, program_pane)
                self._program_starter_threads.append(starter_thread)
                starter_thread.start_thread()

        logging.info("All programs started!")


    def get_view_ref_str(self) -> List[str]:
        ret = []
        for session in self._sessions:
            ret.append(session.name)
        return ret
    # endregion
