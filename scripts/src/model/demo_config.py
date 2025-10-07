import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


# The demo execution script may use python console panels or tmux to display its output
class OutputMode(Enum):
    PYTHON="python"
    TMUX="tmux"


##### YAML key strings for the demo_configuration.yml file


class DemoAttributeIdentifier(Enum):
    OUTPUT_MODE="output_mode"
    PROGRAM_GROUPS="programs"


class ProgramGroupIdentifier(Enum):
    CORE="run_core"
    RIC="run_ric"
    GNB="run_gnb"
    UE= "run_ue"
    MISC= "run_misc"


class ProgramGroupAttributeIdentifier(Enum):
    RESTART_TIMEOUT="restart_timeout_s"
    RESTART_MAX_NUM="max_num_restart"
    PROGRAM_LIST="program_list"


class ProgramAttributeIdentifier(Enum):
    NAME="name"
    STARTING_ORDER="starting_order"
    COMMAND="command"
    WORKING_DIRECTORY="working_directory"
    SUCCESS_INDICATION="success_indication"


##### Dataclass definitions


@dataclass
class DemoProgram:
    """
    Describes a single program/command to be executed.
    A demo setup may consist of several such program instances.
    (E.g. core, ric, ue1, ue2, ... gnb, monitoring1, monitoring2, ..., traffic generation, ...)
    """
    name: Optional[str] = None
    starting_order: Optional[int] = None
    command: Optional[List[str]] = field(default_factory=list)
    working_directory: Optional[str] = None
    success_indication: Optional[List[str]] = field(default_factory=list)


@dataclass
class DemoProgramGroup:
    """
    Describes a set of individual programs/commands to be executed.
    The programs within each set share common attributes.
    A demo setup may consist of several such program group instances.
    """
    group_type: Optional[ProgramGroupIdentifier] = None
    group_name: Optional[str] = None
    restart_timeout: Optional[int] = None
    restart_max_num: Optional[int] = None
    programs: Optional[List[DemoProgram]] = field(default_factory=list)


@dataclass
class DemoCfg:
    """
    Contains all programs/commands to be deployed.
    Individual programs are started in a specified order.
    Each individual program must have a unique name and the starting orders must be strictly increasing.
    """
    config_file_name: Optional[str] = None
    output_mode: Optional[OutputMode] = None
    program_groups: Optional[List[DemoProgramGroup]] = field(default_factory=list)

    def __str__(self):
        retstr = (f"DemoConfig:\n"
                  f"    output_mode={self.output_mode.value}\n"
                  f"    programs:\n")
        for group in self.program_groups:
            retstr += f"        group={group.name}\n"
            retstr += f"            restart_interval={group.restart_timeout}\n"
            retstr += f"            restart_max_num={group.restart_max_num}\n"
            retstr += f"            program_list:\n"
            for program in group.programs:
                retstr += f"                name={program.name}\n"
                retstr += f"                    starting_order={program.starting_order}\n"
                retstr += f"                    command={program.command}\n"
                retstr += f"                    working_directory={program.working_directory}\n"
                retstr += f"                    success_indication={program.success_indication}\n"
        return retstr


    def _check_file_name(self):
        if self.config_file_name is None:
            logging.error("DemoConfig: file_name is None")
            exit(1)


    def _check_program_name(self):
        all_program_names = [str]
        for group in self.program_groups:
            for program in group.programs:
                if program.name is None:
                    logging.error(f"{self.config_file_name}: No name for at least one program!")
                    exit(1)
                all_program_names.append(program.name)
        if len(all_program_names) != len(set(all_program_names)):
            logging.error(f"{self.config_file_name}: All program names must be unique!")
            exit(1)


    def _check_sequence(self):
        all_program_start_numbers = [int]
        for group in self.program_groups:
            for program in group.programs:
                if program.starting_order is None:
                    logging.error(f"{self.config_file_name}: No starting_order for program {program.name}!")
                    exit(1)
                all_program_start_numbers.append(program.starting_order)
        all_program_start_numbers.sort()
        if len(all_program_start_numbers) != len(set(all_program_start_numbers)):
            logging.error(f"{self.config_file_name}: All program starting orders must be unique!")
            exit(1)
        if len(all_program_start_numbers) > 0 >= all_program_start_numbers[0]:
            logging.error(f"{self.config_file_name}: All program starting orders must be larger than 0!")
            exit(1)

    def check_validity(self):
        self._check_file_name()
        self._check_program_name()
        self._check_sequence()