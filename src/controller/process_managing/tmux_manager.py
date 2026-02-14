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
from controller.process_managing.output_piping import OutputPipeListenerThread, OutputPipe
from controller.process_managing.process_manager_base import ProcessManager, GENERAL_SUBPROCESS_TIMEOUT, CHECKUP_PERIOD
from controller.process_managing.program_state_monitor import ProgramRecord, ProgramStateData
from model.utils_config import ProgramState

# Maximum time to wait for tmux pane to become ready after sending commands
PANE_READY_TIMEOUT = 1.0  # seconds


class TmuxRunnerThread:
    def __init__(self, state: ProgramStateData, record: ProgramRecord, tmux_pane: Pane):
        self._program_state: ProgramStateData = state
        self._record: ProgramRecord = record
        self._pane = tmux_pane
        self.program_thread: Thread = Thread()
        self.running = False

    def _runner_thread_funct(self):
        while self.running:
            if not self._program_state.are_preconditions_met():
                # Wait for dependencies to be met. Programs can have two types of dependencies:
                # - depends_on: Programs that must be RUNNING (notified via cv_finished_programs)
                # - depends_on_init: Programs that must be INITIALIZING (notified via cv_initialised_programs)

                if len(self._program_state.program.depends_on_init_names) > 0:
                    with self._record.cv_initialised_programs:
                        self._record.cv_initialised_programs.wait(GENERAL_SUBPROCESS_TIMEOUT)
                elif len(self._program_state.program.depends_on_names) > 0:
                    with self._record.cv_finished_programs:
                        self._record.cv_finished_programs.wait(GENERAL_SUBPROCESS_TIMEOUT)
                else:
                    sleep(CHECKUP_PERIOD)

                if not self._program_state.are_preconditions_met():
                    continue

            # can now start program
            logging.debug(f"Start Program {self._program_state.program.name}")
            self._pane.send_keys(" ".join(self._program_state.program.command))
            if not self._program_state.use_state_checking:
                # Since this program has no state transitions, we immediately consider it running
                self._record.add_finished_program(self._program_state.program.name)
                self._program_state.program_state = ProgramState.RUNNING

            logging.debug(f"Program: {self._program_state.program.name} started")
            break
        logging.debug(f"Ending Program Starter thread {self._program_state.program.name}.")

    def start_thread(self):
        self.running = True
        self.program_thread = Thread(target=self._runner_thread_funct)
        self.program_thread.start()
        logging.debug(f"Program starter thread for {self._program_state.program.name} started")

    def set_stop_signal(self):
        self.running = False

    def join_thread(self):
        self.program_thread.join(timeout=GENERAL_SUBPROCESS_TIMEOUT)


class TmuxManager(ProcessManager):
    def __init__(self, runner: DemoRunner):
        super().__init__(runner)
        # Tmux objects
        self._server = libtmux.Server()
        self._sessions: List[Session] = []
        self._session_prefix = runner.cfg.programs.session_prefix
        self._panes_per_session = runner.cfg.programs.panes_per_session

        # Which program state is associated with which pane?
        self._pane_state_pair: dict[str, ProgramStateData] = {}

        # Threads
        self._program_starter_threads: List[TmuxRunnerThread] = []

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

    def _wait_for_pane_ready(self, pane: Pane, timeout_seconds: float = 1.0) -> bool:
        """
        Wait for a tmux pane to be ready (shell is idle and can accept new commands).
        This ensures that previous send_keys commands (like pipe-pane, cd) have completed.

        Returns True if pane is ready, False if timeout occurred.
        """
        idle_command = os.path.basename(self._server.show_environment()['SHELL'])
        start_time = time.time()
        poll_interval = 0.01

        while (time.time() - start_time) < timeout_seconds:
            if pane.pane_current_command == idle_command:
                return True
            time.sleep(poll_interval)

        logging.warning(f"Pane {pane.pane_id} did not become ready within {timeout_seconds}s")
        return False

    def _get_session_index(self, name: str) -> int:
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
        if not self._validate():
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
            return False
        return True

    # endregion

    # region private_override
    def _handle_restart(self, *args) -> bool:
        # Expect (self, program state)
        if len(args) != 2:
            logging.error(f"Invalid number of arguments for restart handler function! ({len(args)})")
            return False
        if not isinstance(args[1], ProgramStateData):
            logging.error("Invalid parameter for restart handler function!")
            return False
        state: ProgramStateData = args[1]
        for paneid in self._pane_state_pair:
            if self._pane_state_pair[paneid].program.name == state.program.name:
                # send command to this pane to end
                # paneid string has the following structure [sess_name]:[window_nr].[pane_nr]
                # we are interested in session name and pane nr
                sess_nr = self._get_session_index(paneid.split(":")[0])
                if sess_nr < 0:
                    logging.error(f"Invalid session name for program {state.program.name} detected!")
                    continue
                pane_nr = int(paneid.split(".")[-1])
                # We CANNOT use the line below! The reference program_pane does not refer to an up-to-date reference
                # do not use: program_pane = self._sessions[sess_nr].panes[pane_nr]
                self._sessions[sess_nr].panes[pane_nr].send_keys("C-c")
                state.cur_num_restarts = state.cur_num_restarts + 1
                # Wait until program is stopped
                seconds_waited = 0
                idle_command = os.path.basename(self._server.show_environment()['SHELL'])
                while seconds_waited < GENERAL_SUBPROCESS_TIMEOUT:
                    if self._sessions[sess_nr].panes[pane_nr].pane_current_command == idle_command:
                        logging.info(f"Program {state.program.name} has stopped. Restarting ...")
                        state.change_state_to(ProgramState.STOPPED)
                        self._sessions[sess_nr].panes[pane_nr].send_keys(" ".join(state.program.command))
                        return True
                    sleep(CHECKUP_PERIOD)
                    seconds_waited = seconds_waited + CHECKUP_PERIOD
                logging.error(f"Failed to restart program {state.program.name}. Please try to restart it manually.")
                return False
        logging.error(f"Program name {state.program.name} not found!")
        return False

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
                    logging.info(
                        f"Killing session {session.session_name}. Number of sessions remaining: {len(self._sessions) - 1}")
                    session.kill()
                    self._sessions.remove(session)
            # Programs are still running, check again later
            time.sleep(CHECKUP_PERIOD)
            waited_seconds += CHECKUP_PERIOD

        # stop reading from program output and state transition processing
        super().cleanup_and_shutdown()

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
        super().start_programs()
        for program_nr in range(len(self._program_state_data)):
            cur_program = self._program_state_data[program_nr]
            session_nr = program_nr // self._panes_per_session
            pane_nr = program_nr % self._panes_per_session
            if (session_nr >= len(self._sessions)) or (pane_nr >= len(self._sessions[session_nr].panes)):
                logging.error(f"Cannot open program in session pane: session: {session_nr}, pane: {pane_nr}")
            else:
                # start a thread which checks all state changes
                state_check = Thread(target=self._state_checker_thread_func,
                                     args=[cur_program, self._handle_restart, cur_program])
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

                # Wait for pane to be ready before starting the program
                # This ensures pipe-pane and cd commands have completed processing
                # Necessary for fast-starting programs (like zmq_proxy) that output within ~100ms
                if not self._wait_for_pane_ready(program_pane, timeout_seconds=PANE_READY_TIMEOUT):
                    logging.warning(f"Pane for {cur_program.program.name} may not be fully ready, proceeding anyway")

                # execute command inside thread
                starter_thread = TmuxRunnerThread(cur_program, self._program_record, program_pane)
                self._program_starter_threads.append(starter_thread)
                starter_thread.start_thread()

        logging.info("All programs started!")

    def get_view_ref_str(self, **kwargs) -> List[str]:
        """
        expected keyed arguments: none
        Returns the session names generated by this process manager to the view layer.
        """
        ret = []
        for session in self._sessions:
            ret.append(session.name)
        return ret
    # endregion
