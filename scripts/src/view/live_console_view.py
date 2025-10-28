import logging
import signal
import subprocess
from email.headerregistry import Group

from time import sleep
from typing import Optional, List

from rich.live import Live
from rich.panel import Panel
from rich.console import Group

from controller.demo_runner import DemoRunner
from controller.process_managing.process_manager_base import GENERAL_SUBPROCESS_TIMEOUT
from controller.process_managing.subproc_manager import SubprocessManager
from controller.process_managing.tmux_manager import TmuxManager
from model.program_descr_config import OutputMode


class LiveView:
    def __init__(self, runner : DemoRunner):
        self._runner : DemoRunner = runner
        self._is_display_active = False

        if self._runner.cfg.programs.output_mode.value == OutputMode.PYTHON.value:
            self._process_manager = SubprocessManager(runner)
        elif self._runner.cfg.programs.output_mode.value == OutputMode.TMUX.value:
            self._process_manager = TmuxManager(runner)
        else:
            logging.error(f"Invalid output mode {self._runner.cfg.programs.output_mode} for live view runner!")
            exit(1)

    def create_program_panels(self) -> List[Panel]:
        panels = []
        for program in self._process_manager.demo_runner.programs:
            panels.append(Panel(self._process_manager.get_view_ref_str(name=program.name)[0], title=program.name))
        return panels

    def setup(self):
        self._process_manager.setup_program_data()

    def _signal_handler(self, signum, frame):
        """Handle SIGINT (Ctrl+C) and SIGTERM to gracefully shut down all containers."""
        logging.info(f"Received signal {signum}. Stopping all programs...")
        self._is_display_active = False
        self._process_manager.cleanup_and_shutdown()
        exit(0)

    def start_programs(self):
        self._process_manager.start_programs()

    def connect_view(self):

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if self._runner.cfg.programs.output_mode.value == OutputMode.TMUX.value:

            # open tmux session windows -> need list of running session names
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
        elif self._runner.cfg.programs.output_mode.value == OutputMode.PYTHON.value:
            self._is_display_active = True
            with Live(redirect_stderr=False, redirect_stdout=False) as live:
                while self._is_display_active:
                    live.update(Group(*self.create_program_panels()))
                    sleep(0.5) # avoid busy waiting
                live.update("")

        else:
            logging.error(f"Invalid output mode {self._runner.cfg.programs.output_mode} for live view runner!")

        # now wait until we end
        while True:
            sleep(3000)
