import logging
import os
import re
import subprocess
from time import sleep
from typing import List

import libtmux
from libtmux import Session

from demo_runner import DemoRunner
from process_manager_base import ProcessManager, GENERAL_SUBPROCESS_TIMEOUT, CHECKUP_PERIOD

class TmuxManager(ProcessManager):
    def __init__(self, runner : DemoRunner):
        super().__init__(runner)
        self._server = libtmux.Server()
        self._sessions : List[Session] = []
        self._session_prefix = runner.cfg.programs.session_prefix
        self._panes_per_session = runner.cfg.programs.panes_per_session


    def _compute_num_sessions(self) -> int:
        needed_sessions = len(self.demo_runner.get_programs()) // self._panes_per_session
        if len(self.demo_runner.get_programs()) % self._panes_per_session != 0:
            needed_sessions = needed_sessions + 1
        return needed_sessions


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
                        print(f"Will destroy existing session: {next_session_name}")
                        self._server.kill_session(next_session_name)
                        print(f"Session {next_session_name} has been destroyed")
                    else:
                        print(f"Session {next_session_name} already exists! Cannot create session!")
                        return False
                print(f"Create session: {next_session_name}")
                self._sessions.append(self._server.new_session(next_session_name))
        return True


    def _create_panes(self):
        for session in self._sessions:
            for i in range(self._panes_per_session - 1):
                session.active_pane.split()
            session.active_window.select_layout("tiled")


    @staticmethod
    def _is_tmux_installed() -> bool:
        result = subprocess.run(["tmux", "-V"],
                                timeout=GENERAL_SUBPROCESS_TIMEOUT,
                                text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        # Expected output is e.g.: tmux 3.2a
        return re.search("^tmux ", result.stdout) is not None


    def cleanup_and_shutdown(self):
        """Stop and kill all sessions"""
        for session in self._sessions:
            for pane in session.panes:
                pane.send_keys("C-c")
        print("Waiting for all processes to close...")
        # after we send sigint to our programs, we wait until they and only the default shell command is running in tmux
        idle_command = os.path.basename(self._server.show_environment()['SHELL'])
        waited_seconds = 0
        while waited_seconds < GENERAL_SUBPROCESS_TIMEOUT:
            if len(self._sessions) == 0:
                print("Sessions successfully closed!")
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
                    print(f"Killing session {session.session_name}. Number of sessions remaining: {len(self._sessions) - 1}")
                    session.kill()
                    self._sessions.remove(session)
            # Programs are still running, check again later
            sleep(CHECKUP_PERIOD)
            waited_seconds += CHECKUP_PERIOD


    def setup_program_data(self):
        if not self._is_tmux_installed():
            logging.error("Tmux not installed")
            exit(1)
        if not self._generate_detached_sessions(False):
            logging.error("Failed to create tmux sessions!")
            self.cleanup_and_shutdown()
            exit(1)
        self._create_panes()


    def start_programs(self):
        for program_nr in range(len(self.demo_runner.get_programs())):
            cur_program = self.demo_runner.get_programs()[program_nr]
            session_nr = program_nr // self._panes_per_session
            pane_nr = program_nr % self._panes_per_session
            if (session_nr >= len(self._sessions)) or (pane_nr >= len(self._sessions[session_nr].panes)):
                logging.error(f"Cannot open program in session pane: session: {session_nr}, pane: {pane_nr}")
            else:
                # change working directory:
                self._sessions[session_nr].panes[pane_nr].send_keys(f"cd {cur_program.working_directory}")
                # execute command
                self._sessions[session_nr].panes[pane_nr].send_keys(" ".join(cur_program.command))


    def get_view_ref_str(self) -> List[str]:
        ret = []
        for session in self._sessions:
            ret.append(session.name)
        return ret

