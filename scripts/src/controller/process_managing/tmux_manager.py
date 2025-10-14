import logging
import os
import re
import subprocess
from os import mkfifo
from pathlib import Path
from threading import Thread
from time import sleep
from typing import List

import libtmux
from libtmux import Session

from controller.demo_runner import DemoRunner
from controller.process_managing.process_manager_base import ProcessManager, GENERAL_SUBPROCESS_TIMEOUT, CHECKUP_PERIOD
from model.program_descr_config import ProgramDescription

# want to remove color characters and docker "Enable Watch" console artefacts
ansi_escape = re.compile(r'\x1B(?:[0-9@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
docker_enable_watch = re.compile(r'w Enable Watch')

class OutputPipes:
    def __init__(self, program : ProgramDescription, log_location_path: str):
        self.program : ProgramDescription = program
        self.pipe_name : str = f"/tmp/{program.name}"
        self.log_file_name : str = os.path.join(log_location_path, f"{program.name}.log")
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
    def __init__(self, output_pipes : OutputPipes):
        self.thread = None
        self.output_pipes = output_pipes
        self.running = False

    def _thread_funct(self):
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
        logging.info(f"Ending Logging thread {self.output_pipes.pipe_name}")

    def start_thread(self):
        self.running = True
        self.thread = Thread(target=self._thread_funct)
        self.thread.start()


    def stop_thread(self):
        self.running = False
        self.thread.join(timeout=GENERAL_SUBPROCESS_TIMEOUT)



class TmuxManager(ProcessManager):
    def __init__(self, runner : DemoRunner):
        super().__init__(runner)
        self._server = libtmux.Server()
        self._sessions : List[Session] = []
        self._session_prefix = runner.cfg.programs.session_prefix
        self._panes_per_session = runner.cfg.programs.panes_per_session
        self._output_listener_threads : List[OutputPipeListenerThread] = []

    def _compute_num_sessions(self) -> int:
        needed_sessions = len(self.demo_runner.programs) // self._panes_per_session
        if len(self.demo_runner.programs) % self._panes_per_session != 0:
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
            sleep(CHECKUP_PERIOD)
            waited_seconds += CHECKUP_PERIOD
        logging.info("Stopping logging threads ...")
        for thread in self._output_listener_threads:
            thread.stop_thread()


    def setup_program_data(self):
        # create log directory
        Path(self.demo_runner.cfg.programs.log_dir).mkdir(parents=True, exist_ok=True)
        if not self._is_tmux_installed():
            logging.error("Tmux not installed")
            exit(1)
        if not self._generate_detached_sessions(True):
            logging.error("Failed to create tmux sessions!")
            self.cleanup_and_shutdown()
            exit(1)
        self._create_panes()


    def start_programs(self):
        for program_nr in range(len(self.demo_runner.programs)):
            cur_program = self.demo_runner.programs[program_nr]
            session_nr = program_nr // self._panes_per_session
            pane_nr = program_nr % self._panes_per_session
            if (session_nr >= len(self._sessions)) or (pane_nr >= len(self._sessions[session_nr].panes)):
                logging.error(f"Cannot open program in session pane: session: {session_nr}, pane: {pane_nr}")
            else:
                program_pane = self._sessions[session_nr].panes[pane_nr]
                pane_id_str = f"{program_pane.session_name}:{program_pane.window_index}.{program_pane.pane_index}"
                # setup logging
                output_pipe = OutputPipes(cur_program, self.demo_runner.cfg.programs.log_dir)
                logging_thread = OutputPipeListenerThread(output_pipe)
                self._output_listener_threads.append(logging_thread)
                logging_thread.start_thread()
                program_pane.send_keys(f"tmux pipe-pane -t {pane_id_str} 'cat > {output_pipe.pipe_name}'")
                # change working directory:
                program_pane.send_keys(f"cd {cur_program.working_directory}")
                # execute command
                program_pane.send_keys(" ".join(cur_program.command))


    def get_view_ref_str(self) -> List[str]:
        ret = []
        for session in self._sessions:
            ret.append(session.name)
        return ret

