"""
Traffic executor for coordinating traffic transmission.

Manages sender and receiver instances for each UE and orchestrates
time-synchronized traffic transmission based on the traffic plan.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Type, Any

import numpy as np
from tqdm import tqdm

from trafficker.model.traffic_parameters import Direction, TrafficParameters
from trafficker.traffic_handler.netcat_handler import NetcatReceiver, NetcatSender
from trafficker.traffic_handler.traffic_handler import TrafficReceiver, TrafficSender


class TrafficExecutor:
    """
    Executes traffic plan.

    Coordinates multiple UE connections and ensures traffic is sent
    according to the time-slotted traffic plan.
    """

    def __init__(self, traffic_plan: dict):
        """
        Initialize traffic executor.

        Args:
            traffic_plan: Dictionary mapping UE IDs to arrays of traffic
        """
        self.traffic_plan: dict = traffic_plan

    def execute(self,
                parameters: TrafficParameters,
                receiver_class: Type[TrafficReceiver] = NetcatReceiver,
                sender_class: Type[TrafficSender] = NetcatSender):
        """
        Execute traffic plan with configured senders and receivers.

        Sets up sender/receiver pairs for each UE based on traffic direction,
        then executes the traffic plan with time synchronization.

        Args:
            parameters: Global traffic parameters
            receiver_class: Class to use for receiving traffic
            sender_class: Class to use for sending traffic

        Raises:
            KeyError: If UEs in traffic plan don't match parameters
        """
        if parameters.direction == Direction.BIDIRECTIONAL:
            logging.error("Bidirectional traffic is currently unsupported. Use the ping sender/receiver instead.")
            raise RuntimeError("Bidirectional traffic is currently unsupported. Use the ping sender/receiver instead.")
        else:
            if parameters.user_equipments.keys() != self.traffic_plan.keys():
                raise KeyError('Mismatch between the specified UEs and the UEs used for traffic generation. Make sure '
                               'all UEs specified in the traffic section are defined in the user-equipments section.')

            total_steps, ue_ids = self.__log_parameters(parameters)

            # Configure sender/receiver topology based on traffic direction:
            # UL: Single receiver at Core, senders at each UE
            # DL: Receivers at each UE, senders at Core (one per UE)
            senders = {}
            receivers = {}
            core_receiver = receiver_class(parameters, parameters.core_service, parameters.core_address) \
                if parameters.direction == Direction.UE_TO_CORE else None

            for ue_id, conn_info in parameters.user_equipments.items():
                if parameters.direction == Direction.UE_TO_CORE:
                    server_address = parameters.core_address
                    client_service = conn_info['service']
                    receivers[ue_id] = core_receiver  # Only a single server in Core for receiving UL traffic from UEs.
                else:
                    server_address = conn_info['address']
                    client_service = parameters.core_service
                    receivers[ue_id] = receiver_class(parameters, conn_info['service'], server_address)

                senders[ue_id] = sender_class(parameters, client_service, server_address)
                logging.debug(f"Configured {parameters.direction.value} handler for {ue_id} -> {server_address}")

            # Start all receivers and senders
            logging.info(f"Starting receivers and senders for {len(ue_ids)} UE(s)...")
            for ue_id in parameters.user_equipments.keys():
                receivers[ue_id].start_session()
                receivers[ue_id].start_receiver()
                senders[ue_id].start_session()
            logging.info("All receivers and senders started")

            try:
                should_stop = False
                loop_iteration = 0
                with ThreadPoolExecutor(max_workers=len(senders)) as executor:
                    while not should_stop:
                        loop_iteration += 1

                        if parameters.loop:
                            logging.info(f"Starting loop iteration {loop_iteration} (infinite mode)")
                            pbar = tqdm(
                                total=total_steps,
                                desc=f"Pass {loop_iteration}",
                                unit="step",
                                bar_format="{desc}: {n_fmt}/{total_fmt} steps [{elapsed}<{remaining}, {rate_fmt}]",
                                leave=False
                            )
                        else:
                            pbar = tqdm(
                                total=total_steps,
                                desc="Traffic",
                                unit="step",
                                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
                            )

                        # Execute traffic plan in time-synchronized steps
                        for values in zip(*self.traffic_plan.values()):
                            start_time = time.time()
                            step = dict(zip(self.traffic_plan.keys(), values))

                            # Send traffic for all UEs in parallel
                            futures = [executor.submit(senders[key].send_traffic, val) for key, val in step.items()]

                            for future in as_completed(futures):
                                future.result()

                            pbar.update(1)

                            # Sleep (when necessary) to maintain precise time granularity
                            rest_duration = (start_time + (parameters.granularity / 1000)) - time.time()
                            if rest_duration > 0:
                                time.sleep(rest_duration)

                        pbar.close()

                        if parameters.loop:
                            logging.info(f"Loop iteration {loop_iteration} complete")
                        should_stop = not parameters.loop

            finally:
                # Clean shutdown of all connections
                logging.info("Stopping receivers and senders...")
                for ue_id in parameters.user_equipments.keys():
                    receivers[ue_id].stop_receiver()
                    receivers[ue_id].close_session()
                    senders[ue_id].close_session()
                logging.info("All receivers and senders stopped")

    def __log_parameters(self, parameters: TrafficParameters) -> tuple[int, list[Any]]:
        """Log traffic execution parameters and compute total steps and duration for progress bar."""
        max_steps = max(len(arr) for arr in self.traffic_plan.values())
        for ue_id in self.traffic_plan:
            arr = self.traffic_plan[ue_id]
            if len(arr) < max_steps:
                self.traffic_plan[ue_id] = np.pad(arr, (0, max_steps - len(arr)), mode='constant')

        total_steps = max_steps
        total_duration_s = total_steps * parameters.granularity / 1000

        ue_ids = list(parameters.user_equipments.keys())
        logging.info(f"Traffic direction: {parameters.direction.value}, UEs: {ue_ids}, "
                     f"granularity: {parameters.granularity}ms, loop: {parameters.loop}")
        logging.info(f"Traffic plan: {total_steps} steps, ~{total_duration_s:.1f}s total duration")
        return total_steps, ue_ids
