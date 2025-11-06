import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Type

from model.traffic.netcat_handler import NetcatReceiver, NetcatSender
from model.traffic.traffic_config import TrafficParameters, Direction
from model.traffic.traffic_handler import TrafficReceiver, TrafficSender


class TrafficExecutor:

    def __init__(self, traffic_plan: dict):
        self.traffic_plan: dict = traffic_plan

    def execute(self,
                parameters: TrafficParameters,
                receiver_class: Type[TrafficReceiver] = NetcatReceiver,
                sender_class: Type[TrafficSender] = NetcatSender):
        if parameters.direction == Direction.bidirectional:
            print('Generating bidirectional traffic is currently not supported. You can use the ping sender / receiver'
                  'for this.')
        else:
            # For UL: Clients are connections from each UE to the Core. There is only one server handling all incoming
            # traffic from the UEs.
            # For DL: Clients are distinct connection from the Core to each UE. There is one server running on each UE
            # handling all incoming traffic from the Core.
            sender = {}
            receivers = {}
            receiver = receiver_class(parameters, parameters.core_service,
                                      parameters.core_address) if parameters.direction == Direction.ueToCore else None
            for ue_id, conn_info in parameters.user_equipments.items():
                if parameters.direction == Direction.ueToCore:
                    server_address = parameters.core_address
                    client_service = conn_info['service']

                    receivers[ue_id] = receiver  # Only a single server in Core for receiving UL traffic from UEs.
                else:
                    server_address = conn_info['address']
                    client_service = parameters.core_service

                    receivers[ue_id] = receiver_class(parameters, conn_info['service'], server_address)

                sender[ue_id] = sender_class(parameters, client_service, server_address)

            for ue_id in parameters.user_equipments.keys():
                receivers[ue_id].start_session()
                receivers[ue_id].start_receiver()

                sender[ue_id].start_session()

            try:
                stop = False
                with ThreadPoolExecutor(max_workers=len(sender)) as executor:
                    while not stop:
                        for values in zip(*self.traffic_plan.values()):
                            start_time = time.time()
                            step = dict(zip(self.traffic_plan.keys(), values))

                            futures = [executor.submit(sender[key].send_traffic, val) for key, val in step.items()]

                            for future in as_completed(futures):
                                future.result()

                            rest_duration = (start_time + (parameters.granularity / 1000)) - time.time()
                            if rest_duration > 0:
                                time.sleep(rest_duration)
                        stop = not parameters.loop

            finally:
                for ue_id in parameters.user_equipments.keys():
                    receivers[ue_id].stop_receiver()
                    receivers[ue_id].close_session()
                    sender[ue_id].close_session()
