from enum import Enum


class TrafficType(Enum):
    OVERLAP = 'overlap'
    PAUSE = 'pause'
    PERIODIC = 'periodic'
    RANDOM = 'random'
    LOOP = 'loop'
    DISTRIBUTION = 'distribution'
