import time
from typing import Any

from numpy import ndarray, dtype

from model.traffic_config import TrafficParameters
from model.ue_container import UEContainer


class TrafficExecutor:

    def __init__(self, traffic_plan: ndarray[tuple[int], dtype[Any]]):
        self.traffic_plan: ndarray[tuple[int], dtype[Any]] = traffic_plan

    def execute(self, parameters: TrafficParameters):
        ue_container = UEContainer(parameters.workdir)
        ue_container.start_session()

        try:
            stop = False
            while not stop:
                for instant_traffic in self.traffic_plan:
                    start_time = time.time()
                    if (instant_traffic > 0
                            and not ue_container.run_ping(parameters.gnb_address, instant_traffic,
                                                          parameters.granularity)):
                        print('Ping did not run successfully')
                    rest_duration = (start_time + (parameters.granularity / 1000)) - time.time()
                    if rest_duration > 0:
                        time.sleep(rest_duration)
                stop = not parameters.loop
        finally:
            ue_container.close_session()
