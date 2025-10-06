import os
import pathlib
from enum import Enum

FILE_DIR = os.path.join(pathlib.Path(__file__).parent.resolve(), '..')
DEFAULT_CFG_FILE: str = os.path.join(FILE_DIR, '../config/sample_configuration.yml')
DEFAULT_DEMO_CFG_FILE: str = os.path.join(FILE_DIR, '../config/demo_configuration.yml')


class BuildType(Enum):
    NATIVE = 0
    DOCKER = 1


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


MAX_DISPLAY_LINE_LENGTH = 120


class ProgramType(Enum):
    RIC = 0
    CORE = 1
    GNB = 2
    UE = 3

    def __str__(self):
        return self.name


class ProgramState(Enum):
    STOPPED = 0
    INITIALIZING = 1
    RUNNING = 2
    ERROR = 4
    TRIGGER_RESTART = 5
    UNDEFINED = 6

    def __str__(self):
        return self.name
