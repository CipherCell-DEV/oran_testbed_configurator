import time
from typing import Any

from numpy import ndarray, dtype

from model.traffic.netcat_handler import NetcatServer, NetcatClient
from model.traffic.traffic_config import TrafficParameters, Direction
from model.traffic.traffic_handler import TrafficServer, TrafficClient


class TrafficExecutor:

    def __init__(self, traffic_plan: ndarray[tuple[int], dtype[Any]]):
        self.traffic_plan: ndarray[tuple[int], dtype[Any]] = traffic_plan

    def execute(self, parameters: TrafficParameters):
        server_service = parameters.ue_service if parameters.direction == Direction.coreToUE else parameters.core_service
        client_service = parameters.core_service if parameters.direction == Direction.coreToUE else parameters.ue_service
        server_address = parameters.ue_address if parameters.direction == Direction.coreToUE else parameters.core_address

        server: TrafficServer = NetcatServer(parameters.workdir, server_service, server_address)
        client: TrafficClient = NetcatClient(parameters.workdir, client_service, server_address)

        server.start_session()
        client.start_session()

        server.start_server()

        try:
            stop = False
            while not stop:
                for instant_traffic in self.traffic_plan:
                    start_time = time.time()
                    if instant_traffic > 0:
                        client.send_traffic(instant_traffic, parameters.granularity - 10)
                    rest_duration = (start_time + (parameters.granularity / 1000)) - time.time()
                    if rest_duration > 0:
                        time.sleep(rest_duration)
                stop = not parameters.loop
        finally:
            server.stop_server()
            server.close_session()
            client.close_session()
