from enum import Enum


class TrafficType(Enum):
    overlap = 'overlap'
    pause = 'pause'
    periodic = 'periodic'
    random = 'random'
    loop = 'loop'
    distribution = 'distribution'
