import logging
import time
from threading import Condition, Lock
from typing import List

from model.program_descr_config import ProgramDescription
from model.utils_config import ProgramState


class ProgramRecord:
    def __init__(self):
        self._finished_programs: List[str] = []
        self.cv_finished_programs: Condition = Condition()
        self._mutex = Lock()

    def has_program_finished(self, program_name: str) -> bool:
        with self._mutex:
            return program_name in self._finished_programs

    def add_finished_program(self, program_name: str):
        with self.cv_finished_programs:
            with self._mutex:
                self._finished_programs.append(program_name)
            self.cv_finished_programs.notify_all()

    def log_finished_programs(self):
        with self._mutex:
            logging.info(f"Currently running: {self._finished_programs}")


class ProgramStateData:
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

        # only if transitions exist apply transition checking
        if self.program.transition_stop_to_init is not None and self.program.transition_init_run is not None:
            self.use_state_checking = True

    def change_state_on_output(self, output_str : str):
        if self.use_state_checking:
            if self.program_state.value == ProgramState.STOPPED.value:
                if output_str.__contains__(self.program.transition_stop_to_init):
                    self.change_state_to(ProgramState.INITIALIZING)
            elif self.program_state.value == ProgramState.INITIALIZING.value:
                if output_str.__contains__(self.program.transition_init_run):
                    self.change_state_to(ProgramState.RUNNING)
                    self._program_record.add_finished_program(self.program.name)


    def change_state_to(self, state : ProgramState):
        with self.cv_state_change:
            self.last_state_change_ts = time.time()
            self.program_state = state
            self.cv_state_change.notify()

    def are_preconditions_met(self) -> bool:
        all_met = True
        for dep in self.program.depends_on_names:
            all_met = all_met & self._program_record.has_program_finished(dep)
        return all_met
