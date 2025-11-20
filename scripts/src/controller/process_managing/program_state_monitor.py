import logging
import time
from threading import Condition, Lock
from typing import List

from model.program_descr_config import ProgramDescription
from model.utils_config import ProgramState


class ProgramRecord:
    """
    List of program names, which have reached the state RUNNING.
    Beware: Once the state RUNNING has been reached, no further state checking is conducted.
        Elements in the list are never revoked.
    Adding new finished programs and querying the program list is thread safe.
    Everytime a new program name is added to the list, the public condition variable of this class is notified.
    """
    def __init__(self):
        self._initialised_programs: List[str] = []
        self._finished_programs: List[str] = []
        self.cv_initialised_programs: Condition = Condition()
        self.cv_finished_programs: Condition = Condition()
        self._mutex = Lock()

    def has_program_finished(self, program_name: str) -> bool:
        with self._mutex:
            return program_name in self._finished_programs

    def has_program_initialised(self, program_name: str) -> bool:
        with self._mutex:
            return program_name in self._initialised_programs

    def add_intitialised_program(self, program_name: str):
        with self.cv_initialised_programs:
            with self._mutex:
                self._initialised_programs.append(program_name)
            self.cv_initialised_programs.notify_all()

    def add_finished_program(self, program_name: str):
        with self.cv_finished_programs:
            with self._mutex:
                self._finished_programs.append(program_name)
            self.cv_finished_programs.notify_all()

    def log_finished_programs(self):
        with self._mutex:
            logging.debug(f"Currently running: {self._finished_programs}")


class ProgramStateData:
    """
    This class encapsulates the state of a program and contains all necessary date for program timeout handling
    and state monitoring.
    This class assigns a state to a program. Whenever this state is changed,
    a public condition variable is notified.
    If the program reaches the running state, the program record containing the list of all running programs is updated.
    """
    def __init__(self, program : ProgramDescription, timeout : int, num_restarts : int, record : ProgramRecord):
        self.program : ProgramDescription = program
        self.program_timeout : int = timeout
        self.program_num_restarts : int = num_restarts
        self.cur_num_restarts : int = 0
        self.program_state : ProgramState = ProgramState.STOPPED
        self.last_state_change_ts = time.time()
        self._program_record : ProgramRecord = record
        self.cv_state_change : Condition = Condition()
        self.use_state_checking : bool = False

        # only if transitions exists apply transition checking
        if self.program.transition_stop_to_init is not None and self.program.transition_init_run is not None:
            self.use_state_checking = True

    def change_state_on_output(self, output_str : str):
        """
        This function handles state transitions. A state transition may be triggered by a certain string
        inside a line of the program output.
        E.g. A program printing "Initialization successful" may indicate a successful transition from
            INITIALIZING to RUNNING.
        The exact strings to be checked for are defined in the demo configuration.
        """
        if self.use_state_checking:
            if self.program_state.value == ProgramState.STOPPED.value:
                if output_str.__contains__(self.program.transition_stop_to_init):
                    self.change_state_to(ProgramState.INITIALIZING)
                    self._program_record.add_intitialised_program(self.program.name)
            elif self.program_state.value == ProgramState.INITIALIZING.value:
                if output_str.__contains__(self.program.transition_init_run):
                    self.change_state_to(ProgramState.RUNNING)
                    self._program_record.add_finished_program(self.program.name)


    def change_state_to(self, state : ProgramState):
        """
        Change program state and notify all waiting threads.
        """
        with self.cv_state_change:
            self.last_state_change_ts = time.time()
            self.program_state = state
            self.cv_state_change.notify()

    def are_preconditions_met(self) -> bool:
        """
        Programs may depend on each other. As such, they need to regularly check the program
         record to see which program is already running.
        """
        all_met = True
        for dep in self.program.depends_on_names:
            all_met = all_met & self._program_record.has_program_finished(dep)
        for dep in self.program.depends_on_init_names:
            all_met = all_met & self._program_record.has_program_initialised(dep)
        return all_met
