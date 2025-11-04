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
                receiver_class: Type[TrafficServer] = NetcatServer,
                sender_class: Type[TrafficClient] = NetcatClient):
        if parameters.direction == Direction.bidirectional:
            print('Generating bidirectional traffic is currently not supported')
        else:
            # For UL: Clients are connections from each UE to the Core. There is only one server handling all incoming
            # traffic from the UEs.
            # For DL: Clients are distinct connection from the Core to each UE. There is one server running on each UE
            # handling all incoming traffic from the Core.
            sender = {}
            receivers = {}
            receiver = receiver_class(parameters.workdir, parameters.core_service, parameters.core_address,
                                      use_nist=parameters.use_nist, nist_vm=parameters.nist_vm) \
                if parameters.direction == Direction.ueToCore else None
            for ue_id, conn_info in parameters.user_equipments.items():
                if parameters.direction == Direction.ueToCore:
                    server_address = parameters.core_address
                    server_service = parameters.core_service
                    client_service = conn_info['service']
                else:
                    server_address = conn_info['address']
                    server_service = conn_info['service']
                    client_service = parameters.core_service

                sender[ue_id] = sender_class(parameters.workdir, client_service, server_address,
                                             use_nist=parameters.use_nist, nist_vm=parameters.nist_vm)
                if parameters.direction == Direction.coreToUE:
                    receivers[ue_id] = receiver_class(parameters.workdir, server_service, server_address,
                                                      use_nist=parameters.use_nist, nist_vm=parameters.nist_vm)
                else:
                    receivers[ue_id] = receiver

            for ue_id in parameters.user_equipments.keys():
                receivers[ue_id].start_session()
                receivers[ue_id].start_receiver()

                sender[ue_id].start_session()

            try:
                stop = False
                while not stop:
                    with ThreadPoolExecutor(max_workers=len(sender)) as executor:
                        for values in zip(*self.traffic_plan.values()):
                            start_time = time.time()
                            step = dict(zip(self.traffic_plan.keys(), values))

                            futures = [executor.submit(sender[key].send_traffic, val) for key, val in step.items()]

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
                    receivers[ue_id].stop_receiver()
                    receivers[ue_id].close_session()
                    sender[ue_id].close_session()
