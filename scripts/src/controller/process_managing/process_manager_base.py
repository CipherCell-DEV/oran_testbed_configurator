from abc import ABC
from typing import Optional

from demo_runner import DemoRunner


class ProcessManager(ABC):
    def __init__(self, runner: DemoRunner):
        self.demo_runner = runner