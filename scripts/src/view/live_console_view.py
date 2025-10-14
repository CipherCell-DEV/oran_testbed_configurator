import logging
import signal
import subprocess
from typing import Optional

from controller.demo_runner import DemoRunner
from controller.process_managing.process_manager_base import ProcessManager, GENERAL_SUBPROCESS_TIMEOUT
from controller.process_managing.subproc_manager import SubprocessManager
from controller.process_managing.tmux_manager import TmuxManager
from model.program_descr_config import OutputMode, TerminalDescription


class LiveView:
    def __init__(self, runner : DemoRunner):
        self._runner : DemoRunner = runner
        self._process_manager : ProcessManager

        if self._runner.cfg.programs.output_mode.value == OutputMode.PYTHON.value:
            self._process_manager = SubprocessManager(runner)
        elif self._runner.cfg.programs.output_mode.value == OutputMode.TMUX.value:
            self._process_manager = TmuxManager(runner)
        else:
            logging.error(f"Invalid output mode {self._runner.cfg.programs.output_mode} for live view runner!")
            exit(1)


    def setup(self):
        self._process_manager.setup_program_data()

    def _signal_handler(self, signum, frame):
        """Handle SIGINT (Ctrl+C) and SIGTERM to gracefully shutdown all containers."""
        logging.info(f"Received signal {signum}. Stopping all programs...")
        self._process_manager.cleanup_and_shutdown()
        exit(0)

    def start_programs(self):
        self._process_manager.start_programs()

    def connect_view(self):

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if self._runner.cfg.programs.output_mode.value == OutputMode.TMUX.value:

            # open tmux session windows -> need running session names
            refs = self._process_manager.get_view_ref_str()
            for ref in refs:
                # opening terminal windows is platform dependent
                # construct command from config
                args = []
                tmux_terminal = self._runner.cfg.programs.get_used_terminal_data()
                if tmux_terminal is not None:
                    if tmux_terminal.subproc_prefix is not None:
                        args.extend(tmux_terminal.subproc_prefix)
                    args.append(f"tmux attach-session -t {ref}")
                    if tmux_terminal.subprocess_postfix is not None:
                        args.extend(tmux_terminal.subprocess_postfix)
                subprocess.run(args,
                               timeout=GENERAL_SUBPROCESS_TIMEOUT,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
            # now wait until we end
            while True:
                pass
        else:
            logging.error(f"Invalid output mode {self._runner.cfg.programs.output_mode}")