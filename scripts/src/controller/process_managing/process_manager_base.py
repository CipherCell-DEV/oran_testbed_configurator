import logging
import signal
from abc import ABC
from typing import List

from demo_runner import DemoRunner

GENERAL_SUBPROCESS_TIMEOUT = 20
CHECKUP_PERIOD = 2


class ProcessManager(ABC):
    def __init__(self, runner: DemoRunner):
        self.demo_runner = runner

    def setup_program_data(self):
        raise NotImplementedError("Base class does not implement setup_program_data")

    def start_programs(self):
        raise NotImplementedError("Base class does not implement start_programs")

    def get_view_ref_str(self) -> List[str]:
        raise NotImplementedError("Base class does not implement get_view_ref_str")

    def cleanup_and_shutdown(self):
        raise NotImplementedError("Base class does not implement _cleanup_and_shutdown")
