"""
Traffic Generator - Execute network traffic patterns in dockerized O-RAN deployments.

This module provides a command-line interface for generating and executing
network traffic patterns based on YAML configuration files. It supports
visualization of traffic plans and execution with socket-based communication.

Example Usage:
    # Execute traffic with default configuration
    python trafficker.py

    # Execute with custom configuration and plot before execution
    python trafficker.py --config my_traffic.yaml

    # Only plot traffic, do not execute it
    python trafficker.py --config my_traffic.yaml --plot --no-exec
"""

import argparse
import logging
import os
import sys

from trafficker.core.traffic_executor import TrafficExecutor
from trafficker.core.traffic_parser import TrafficConfigParser
from trafficker.core.traffic_plan_generator import TrafficPlanGenerator
from trafficker.model.traffic_parameters import TrafficParameters
from trafficker.traffic_handler.pysocket_handler import PySocketReceiver, PySocketSender

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute traffic in Docker Compose container.')
    parser.add_argument('--config', default=os.path.join(os.path.dirname(__file__), '../config/sample_traffic.yaml'),
                        help='Path to traffic config YAML')
    parser.add_argument('--plot', action='store_true', help='Visualize traffic plan before execution')
    parser.add_argument('--time-unit', choices=['ms', 's', 'm', 'h'], default='m', help='Time unit for plot')
    parser.add_argument('--no-exec', action='store_false', help='Do not execute traffic plan')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        logging.info(f"Loading config: {args.config}")
        params = TrafficParameters.load_yaml(args.config)
        traffic = TrafficConfigParser.load_yaml(args.config)

        logging.debug(f"Parameters: granularity={params.granularity}ms, direction={params.direction.value}, "
                      f"loop={params.loop}, UEs={list(params.user_equipments.keys())}")

        gen = TrafficPlanGenerator(params)
        gen.from_plan(traffic)

        if args.plot:
            logging.info(f"Plotting (unit: {args.time_unit})... Close to start execution or Ctrl+C to abort")
            gen.plot(time_unit=args.time_unit)

        if args.no_exec:
            logging.info("Executing traffic...")
            TrafficExecutor(gen.traffic).execute(params, PySocketReceiver, PySocketSender)
            logging.info("Traffic execution complete")

    except KeyboardInterrupt:
        logging.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
