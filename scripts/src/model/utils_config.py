import os
import pathlib
from enum import Enum

FILE_DIR = os.path.join(pathlib.Path(__file__).parent.resolve(), '..')
DEFAULT_CFG_FILE: str = os.path.join(FILE_DIR, '../config/sample_configuration.yml')


class BuildType(Enum):
    NATIVE = 0
    DOCKER = 1


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


MAX_DISPLAY_LINE_LENGTH = 120
