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
from view.dialog import ask_choice


class LiveView:
    def __init__(self, runner: DemoRunner):
        self._runner: DemoRunner = runner
        self._is_display_active = False

        if self._runner.cfg.programs.output_mode.value == OutputMode.PYTHON.value:
            self._process_manager = SubprocessManager(runner)
        elif self._runner.cfg.programs.output_mode.value == OutputMode.TMUX.value:
            self._process_manager = TmuxManager(runner)
        else:
            logging.error(f"Invalid output mode {self._runner.cfg.programs.output_mode} for live view runner!")
            exit(1)

    def _create_program_panels(self) -> List[Panel]:
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

    @staticmethod
    def _run_open_terminal_command(commands: List[List[str]]):
        for command in commands:
            # TODO to open a terminal on macOS requires a osascript which can not easily seperated into prefix and postfix
            if command[0] == 'osascript':
                cmd = command[:2]
                osascript_command = '\n'.join(command[2:-1]).replace('{{command}}', command[-1])
                subprocess.run(cmd + [osascript_command])
            else:
                subprocess.run(command,
                               timeout=GENERAL_SUBPROCESS_TIMEOUT,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    def _reselect_terminal(self, ref_strings: List[str]) -> bool:
        all_programs = self._process_manager.demo_runner.cfg.programs.get_terminal_name_list()
        all_programs.append("None")
        choice = ask_choice("Which terminal do you want to use:",
                            all_programs,
                            1)
        logging.info(f"Terminal choice: {choice}: {all_programs[choice - 1]}")
        if choice == len(all_programs):
            # no terminal chosen
            return False
        else:
            commands = self._construct_terminal_command(all_programs[choice - 1], ref_strings)
            self._run_open_terminal_command(commands)
            return True


    def _construct_terminal_command(self, terminal_name : str, ref_strings: List[str]) -> List[List[str]]:
        """
        Constructs terminal commands to open the tmux windows for the given terminal.
        ref_strings are passed from the process control to the view layer for identification or other purposes
            (depends on process manager). This helper function expects tmux session names here.
        """
        terminal = self._process_manager.demo_runner.cfg.programs.get_terminal_by_name(terminal_name)
        subprocess_commands = []
        if terminal is not None:
            for ref in ref_strings:
                curr_command = []
                if terminal.subproc_prefix is not None:
                    curr_command.extend(terminal.subproc_prefix)
                curr_command.append(f"tmux attach-session -t {ref}")
                if terminal.subprocess_postfix is not None:
                    curr_command.extend(terminal.subprocess_postfix)
                subprocess_commands.append(curr_command)
        return subprocess_commands

    def _ask_for_open_tmux(self):
        refs = self._process_manager.get_view_ref_str()
        logging.info(f"The following tmux sessions are currently running: {', '.join(refs)}")
        tmux_terminal = self._runner.cfg.programs.get_used_terminal_data()
        display_instruction = False
        if tmux_terminal is not None:
            commands = self._construct_terminal_command(tmux_terminal.name, refs)
            logging.info(f"Currently selected terminal: {tmux_terminal.name}")
            logging.info("About to execute the following commands to attach to tmux sessions:")
            for command in commands:
                logging.info(f"\t{' '.join(command)}")
            choice = ask_choice("Do you want me to execute the commands listed above?",
                                ["Yes, open the terminal windows for me",
                                 "No, just keep running the demo in the background",
                                 "No, choose other terminal instead"],
                                default=1)
            if choice == 1:
                self._run_open_terminal_command(commands)

            elif choice == 2:
                display_instruction = True

            elif choice == 3:
                display_instruction = not self._reselect_terminal(refs)

        else:
            logging.info(f"No terminal is configured. Will not open tmux windows for you.")
            display_instruction = True

        if display_instruction:
            logging.info("The programs are now running inside tmux.")
            logging.info(
                "You can connect to the tmux session windows anytime by running the following commands in a terminal of your choice:")
            for ref in refs:
                logging.info(f"\t tmux attach-session -t {ref}")

        logging.info("Programs are running. Press Ctrl+C to close software.")

    def start_programs(self):
        self._process_manager.start_programs()

    def connect_view(self):

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if self._runner.cfg.programs.output_mode.value == OutputMode.TMUX.value:
            # open tmux session windows -> need list of running session names
            self._ask_for_open_tmux()
        elif self._runner.cfg.programs.output_mode.value == OutputMode.PYTHON.value:
            self._is_display_active = True
            with Live(redirect_stderr=False, redirect_stdout=False) as live:
                while self._is_display_active:
                    live.update(Group(*self._create_program_panels()))
                    sleep(0.5)  # avoid busy waiting
                live.update("")

        else:
            logging.error(f"Invalid output mode {self._runner.cfg.programs.output_mode} for live view runner!")

        # now wait until we end
        while True:
            sleep(3000)
