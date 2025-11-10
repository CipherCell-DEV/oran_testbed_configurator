import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from controller.utils import get_operating_system, OperatingSystem

"""The demo execution script may use python console panels or tmux to display its output"""


class OutputMode(Enum):
    PYTHON = "python"
    TMUX = "tmux"


class ProgramGroupIdentifier(Enum):
    CORE = "run_core"
    RIC = "run_ric"
    GNB = "run_gnb"
    UE = "run_ue"
    MISC = "run_misc"


"""YAML key strings for the demo_configuration.yml file"""


class TerminalIdentifiers(Enum):
    USED_TERMINAL = "default_terminal"
    TERMINALS = "terminals"
    SUBPROC_PREFIX = "subprocess_prefix"
    SUBPROC_POSTFIX = "subprocess_postfix"


class OutputIdentifiers(Enum):
    OUTPUT_MODE = "output_mode"
    OUTPUT_SETTINGS = "output_settings"
    LOG_DIR = "log_dir"
    SESSION_PREFIX = "session_prefix"
    PANES_PER_SESSION = "panes_per_session"
    SHOW_NUM_LINES = "show_num_lines"


class ProgramIdentifiers(Enum):
    PROGRAM_GROUPS = "programs"
    RESTART_TIMEOUT = "restart_timeout_s"
    RESTART_MAX_NUM = "max_num_restart"
    PROGRAM_LIST = "program_list"
    PROGRAM_NAME = "name"
    PROGRAM_DEPENDS = "depends_on"
    PROGRAM_COMMAND = "command"
    PROGRAM_WORKING_DIRECTORY = "working_directory"
    PROGRAM_STATE_TRANSITIONS = "state_transitions"
    PROGRAM_TRANSITION_STOP_INIT = "stop_to_init"
    PROGRAM_TRANSITION_INIT_RUN = "init_to_running"


"""Dataclasses and functions"""


@dataclass
class TerminalDescription:
    """
    We want to open a terminal window to show the running tmux sessions(if tmux is set as output_mode)
    As there is no platform independent way to do this (tell me if you think otherwise!), we need additional
    info on the installed terminal. This is used in a python subprocess.run call to open a window attached
    to a tmux session.
    We assume the following systax: [subprocess_prefix] [tmux attach-session -t .....] [subprocess_postfix]
    Example for gnome terminal:
    gnome-terminal -- bash -c tmux attach-session -t ...
    subprocess_idle is the command which is running inside tmux. Normally this is the shell i.e. bash, sh, etc.
    subprocess_idle is used to differentiate between "A program is currently running in tmux" and
    "The tmux pane is ready to start a program"
    """
    name: Optional[str] = None
    subproc_prefix: Optional[List[str]] = None
    subprocess_postfix: Optional[List[str]] = None


    def __str__(self):
        ret_str = f"Terminal: {self.name}\n"
        ret_str += f"Subproc prefix: {self.subproc_prefix}\n"
        ret_str += f"Subproc postfix: {self.subprocess_postfix}\n"


class ProgramDescription:
    """
    Describes a single program/command to be executed.
    A setup may consist of several such program instances.
    (E.g. core, ric, ue1, ue2, ... gnb, monitoring1, monitoring2, ..., traffic generation, ...)
    """
    def __init__(self):
        self.name: Optional[str] = None
        self.depends_on_names: List[str] = []
        self.command: List[str] = []
        self.working_directory: Optional[str] = None
        self.transition_stop_to_init: Optional[str] = None
        self.transition_init_run: Optional[str] = None
        self.timeout : int = 0 # in seconds
        self.max_num_restarts : int = 0


    def __str__(self) -> str:
        ret_str = f"name={self.name}\n"
        ret_str += f"    depends_on={self.depends_on_names}\n"
        ret_str += f"    command={self.command}\n"
        ret_str += f"    working_directory={self.working_directory}\n"
        ret_str += f"    transition_stop_to_init={self.transition_stop_to_init}\n"
        ret_str += f"    transition_init_run={self.transition_init_run}\n"
        ret_str += f"    timeout={self.timeout}\n"
        ret_str += f"    max_num_restarts={self.max_num_restarts}\n"
        return ret_str


    def update_group_data(self, timeout : int, max_num_restarts : int):
        """Some program attributes are defined per program group"""
        self.timeout = timeout
        self.max_num_restarts = max_num_restarts

class ProgramDescrGroup:
    """
    Describes a set of individual programs/commands to be executed.
    The programs within each set share common attributes.
    Group names must be unique.
    """
    def __init__(self):
        self.group_type: Optional[ProgramGroupIdentifier] = None
        self.group_name: Optional[str] = None
        self.restart_timeout: Optional[int] = None
        self.restart_max_num: Optional[int] = None
        self.programs: List[ProgramDescription] = []

    def __str__(self) -> str:
        ret_str = f"group_type={self.group_type}\n"
        ret_str += f"group_name={self.group_name}\n"
        ret_str += f"restart_interval={self.restart_timeout}\n"
        ret_str += f"restart_max_num={self.restart_max_num}\n"
        ret_str += f"program_list:\n"
        for program in self.programs:
            ret_str += program.__str__()
        return ret_str


class ProgramDescriptionCfg:
    """
    Contains all programs/commands to be deployed.
    Individual programs may depend on other programs.
    Each individual program must have a unique name.
    """
    def __init__(self):
        self.config_file_path: Optional[str] = None
        self.output_mode: Optional[OutputMode] = None
        self.log_dir: Optional[str] = None
        self.session_prefix: Optional[str] = None # used for tmux output
        self.panes_per_session: int = 0 # used for tmux output
        self.show_num_lines: int = 0 # used for python output
        self._used_terminal: Optional[TerminalDescription] = None
        self.terminal_descriptions: List[TerminalDescription] = []
        self.program_groups: List[ProgramDescrGroup] = []


    def __str__(self) -> str:
        term_str = ""
        for term in self.terminal_descriptions:
            term_str += term.__str__()
        ret_str = (f"ProgramConfig:{self.config_file_path}\n"
                  f"output_mode={self.output_mode.value}\n"
                  f"log_dir={self.log_dir}\n" 
                  f"used_terminal={self._used_terminal}\n" 
                  f"terminals:\n"
                  f"{term_str}"
                  f"session_prefix={self.session_prefix}\n"
                  f"panes_per_session={self.panes_per_session}\n"
                  f"show_num_lines={self.show_num_lines}\n"
                  f"programs:\n")
        for group in self.program_groups:
            ret_str += group.__str__()
        return ret_str

    def _set_terminal_by_name_pref(self, name_prefix : str) -> List[TerminalDescription]:
        suitable_terms: List[TerminalDescription] = []
        for term in self.terminal_descriptions:
            if term.name.startswith(name_prefix):
                suitable_terms.append(term)
        if len(suitable_terms) == 0:
            logging.warning(f"No matching {name_prefix} terminal found. Use Terminal {self.terminal_descriptions[0].name} instead!")
            self._used_terminal = self.terminal_descriptions[0]
        else:
            logging.info(f"Found {name_prefix} terminal {suitable_terms[0].name}")
            self._used_terminal = suitable_terms[0]
        return suitable_terms


    def _check_valid_terminal(self) -> bool:
        if self.terminal_descriptions is None or len(self.terminal_descriptions) == 0:
            logging.error("No terminals are defined in the demo configuration!")
            return False

        used_os = None
        try:
            used_os = get_operating_system()
        except ValueError:
            logging.warning(f"Failed to determine Operating System!")

        if self._used_terminal is None or self._used_terminal == "":
            # try to find OS compatible terminal
            logging.warning(f"{self.config_file_path}: No default terminal provided!")
            if used_os is None:
                logging.warning(f"Use terminal {self.terminal_descriptions[0].name} as default.")
                self._used_terminal = self.terminal_descriptions[0]
                return True
            if used_os is OperatingSystem.WINDOWS:
                self._set_terminal_by_name_pref("windows_")
                return True
            if used_os is OperatingSystem.LINUX:
                self._set_terminal_by_name_pref("linux_")
                return True
            if used_os is OperatingSystem.MACOS:
                self._set_terminal_by_name_pref("apple_")
                return True
        else:
            # fix mismatching terminal
            if used_os is OperatingSystem.LINUX and not self._used_terminal.name.startswith("linux_"):
                logging.warning(f"Terminal {self.terminal_descriptions[0].name} is not a Linux terminal!")
                self._set_terminal_by_name_pref("linux_")
            if used_os is OperatingSystem.MACOS and not self._used_terminal.name.startswith("apple_"):
                logging.warning(f"Terminal {self.terminal_descriptions[0].name} is not a mac terminal!")
                self._set_terminal_by_name_pref("apple_")

        for term in self.terminal_descriptions:
            if term.name == self._used_terminal.name:
                return True
        logging.error(f"{self.config_file_path}: Used terminal is not in terminal list!")
        return False


    def _check_output_settings(self) -> bool:
        if self.output_mode == OutputMode.PYTHON:
            if self.show_num_lines is None or self.show_num_lines <= 0:
                logging.error(f"{self.config_file_path}: Invalid number of output lines for python monitoring (have {self.show_num_lines})!")
                return False
            return True
        if self.output_mode == OutputMode.TMUX:
            if (self.session_prefix is None) or (self.session_prefix == ""):
                logging.error(f"{self.config_file_path}: Tmux session prefix must not be empty!")
                return False
            if (len(self.session_prefix.split()) <= 0) or (len(self.session_prefix.split()) >= 2):
                logging.error(f"{self.config_file_path}: Tmux session prefix must have no whitespaces (have {self.session_prefix})!")
                return False
            if (self.panes_per_session is None) or (self.panes_per_session <= 0):
                logging.error(f"{self.config_file_path}: Tmux panes_per_session must be positive (have {self.panes_per_session})!")
                return False
            return True
        logging.error(f"{self.config_file_path}: Invalid output mode!")
        return False


    def _check_program(self) -> bool:
        all_program_names = [str]
        for group in self.program_groups:
            if (group.restart_timeout is None) or (group.restart_timeout <= 0):
                logging.error(f"{self.config_file_path}: {group.restart_timeout} restart time is invalid!")
                return False
            if (group.restart_max_num is None) or (group.restart_max_num < 0):
                logging.error(f"{self.config_file_path}: {group.restart_max_num} restart number is invalid!")
                return False
            for program in group.programs:
                if (program.name is None) or (program.name == ""):
                    logging.error(f"{self.config_file_path}: No name for at least one program!")
                    return False
                if (len(program.name.split()) <= 0) or (len(program.name.split()) >= 2):
                    logging.error(f"{self.config_file_path}: Invalid program name: {program.name}. Name must have no whitespaces!")
                    return False
                if program.transition_stop_to_init is None or len(program.transition_stop_to_init) == 0:
                    if program.transition_init_run is None or len(program.transition_init_run) == 0:
                        logging.debug(f"{program.name}: Partial transition definition (missing init_to_run)")
                if program.transition_init_run is None or len(program.transition_init_run) == 0:
                    if program.transition_stop_to_init is None or len(program.transition_stop_to_init) == 0:
                        logging.debug(f"{program.name}: Partial transition definition (missing stop_to_init)")
                all_program_names.append(program.name)
        if len(all_program_names) != len(set(all_program_names)):
            logging.error(f"{self.config_file_path}: All program names must be unique!")
            return False
        # dependencies must refer to program names
        for group in self.program_groups:
            for program in group.programs:
                for dependency in program.depends_on_names:
                    if dependency not in all_program_names:
                        logging.error(f"{self.config_file_path}: Program {program.name}: Dependency {dependency} is not in program list!")
                        return False
        return True


    def _get_programs_of_group(self, group_id: ProgramGroupIdentifier) -> List[ProgramDescription]:
        for group in self.program_groups:
            if group.group_type == group_id:
                return group.programs
        return []


    def check_validity(self) -> bool:
        if self.config_file_path is None or self.config_file_path == "":
            logging.error("Missing program configuration file path!")
            return False
        return self._check_output_settings() and self._check_program() and self._check_valid_terminal()


    def get_ric_programs(self) -> List[ProgramDescription]:
        ret = self._get_programs_of_group(ProgramGroupIdentifier.RIC)
        if len(ret) > 1:
            logging.warning(f"{self.config_file_path}: More than one ric program defined!")
        return ret

    def get_core_programs(self) -> List[ProgramDescription]:
        ret = self._get_programs_of_group(ProgramGroupIdentifier.CORE)
        if len(ret) > 1:
            logging.warning(f"{self.config_file_path}: More than one core program defined!")
        return ret

    def get_gnb_programs(self) -> List[ProgramDescription]:
        ret = self._get_programs_of_group(ProgramGroupIdentifier.GNB)
        if len(ret) > 1:
            logging.warning(f"{self.config_file_path}: More than one gnb program defined!")
        return ret

    def get_ue_programs(self) -> List[ProgramDescription]:
        ret = self._get_programs_of_group(ProgramGroupIdentifier.UE)
        return ret

    def get_misc_programs(self) -> List[ProgramDescription]:
        ret = self._get_programs_of_group(ProgramGroupIdentifier.MISC)
        return ret

    def get_used_terminal_data(self) -> TerminalDescription | None:
        return self._used_terminal

