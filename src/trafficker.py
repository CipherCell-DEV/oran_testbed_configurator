import argparse
import os

from controller.traffic.traffic_executor import TrafficExecutor
from controller.traffic.traffic_parser import TrafficConfigParser
from controller.traffic.traffic_plan_generator import TrafficPlanGenerator
from model.traffic.pysocket_handler import PySocketReceiver, PySocketSender
from model.traffic.traffic_config import TrafficParameters

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute periodic traffic in the Docker Compose container.')
    parser.add_argument('--config', type=str,
                        default=os.path.join(os.path.dirname(__file__), 'config/sample_traffic.yaml'),
                        help='Path to sample_traffic.yaml config')
    args = parser.parse_args()

    parameters = TrafficParameters.load_yaml(args.config)
    traffic_config = TrafficConfigParser.load_yaml(args.config)

    generator = TrafficPlanGenerator(parameters)
    generator.from_plan(traffic_config)
    generator.plot(time_unit='m')

    executor = TrafficExecutor(generator.traffic)
    executor.execute(parameters, receiver_class=PySocketReceiver, sender_class=PySocketSender)
