import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Type

from model.traffic.netcat_handler import NetcatServer, NetcatClient
from model.traffic.traffic_config import TrafficParameters, Direction
from model.traffic.traffic_handler import TrafficServer, TrafficClient


class TrafficExecutor:

    def __init__(self, traffic_plan: dict):
        self.traffic_plan: dict = traffic_plan

    def execute(self,
                parameters: TrafficParameters,
                server_class: Type[TrafficServer] = NetcatServer,
                client_class: Type[TrafficClient] = NetcatClient):
        if parameters.direction == Direction.bidirectional:
            print('Generating bidirectional traffic is currently not supported')
        elif parameters.direction == Direction.ueToCore:
            print('Generating Uplink traffic is currently not supported')
        elif parameters.direction == Direction.coreToUE:
            clients = {}  # Always running on core, one object for each ue that traffic needs to be sent to
            servers = {}  # UEs
            for ue_id, conn_info in parameters.user_equipments.items():
                clients[ue_id] = client_class(parameters.workdir, parameters.core_service, conn_info['address'],
                                              use_nist=parameters.use_nist)
                servers[ue_id] = server_class(parameters.workdir, conn_info['service'], conn_info['address'],
                                              use_nist=parameters.use_nist)

            for ue_id in parameters.user_equipments.keys():
                servers[ue_id].start_session()
                servers[ue_id].start_server()

                clients[ue_id].start_session()

            try:
                stop = False
                while not stop:
                    with ThreadPoolExecutor(max_workers=len(clients)) as executor:
                        for values in zip(*self.traffic_plan.values()):
                            start_time = time.time()
                            step = dict(zip(self.traffic_plan.keys(), values))

                            futures = [
                                executor.submit(clients[key].send_traffic, val)
                                for key, val in step.items()
                            ]

                            for future in as_completed(futures):
                                future.result()

                            rest_duration = (start_time + (parameters.granularity / 1000)) - time.time()
                            if rest_duration > 0:
                                time.sleep(rest_duration)
                            if rest_duration <= 0:
                                print(rest_duration)
                    stop = not parameters.loop

            finally:
                for ue_id in parameters.user_equipments.keys():
                    servers[ue_id].stop_server()
                    servers[ue_id].close_session()
                    clients[ue_id].close_session()
