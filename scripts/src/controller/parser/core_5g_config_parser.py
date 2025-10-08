import ipaddress
import logging

from controller.parser.parser_utils import ParsingUtils
from model.core_config import Core5GCfg, CoreFieldIdentifiers, ALLOWED_IMPLEMENTATION_LIST, Core5GNetworkCfg


class Core5GConfigParser:

    @staticmethod
    def _parse_5g_network_config(params: dict) -> Core5GNetworkCfg:
        if CoreFieldIdentifiers.NETWORK not in params:
            raise KeyError(f"Missing required parameter for 5GC config: '{CoreFieldIdentifiers.NETWORK}'")

        network_cfg = params[CoreFieldIdentifiers.NETWORK]
        core_network = Core5GNetworkCfg()

        field_map = {
            "ip": (CoreFieldIdentifiers.CORE_IP, ipaddress.IPv4Address, "No IP address specified for 5G core"),
            "subnet": (CoreFieldIdentifiers.SUBNET, ipaddress.IPv4Network, "No subnet specified for 5G core"),
            "mongodb_ip": (CoreFieldIdentifiers.MONGO_DB_IP, ipaddress.IPv4Address,
                           "No IP address specified for 5G core MongoDB")
        }

        for attr, (key, cast, err_msg) in field_map.items():
            if key in network_cfg:
                setattr(core_network, attr, cast(network_cfg[key]))
            else:
                raise KeyError(err_msg)

        return core_network

    @staticmethod
    def parse_5g_cfg(params: dict) -> Core5GCfg:
        """ Parse the 5G Core Network configuration. """
        logging.info("Parse 5GC Core Configuration")
        cfg = Core5GCfg()

        cfg.build_type = ParsingUtils.parse_build_type(params, '5g Core')
        cfg.implementation = ParsingUtils.parse_implementation(params, ALLOWED_IMPLEMENTATION_LIST, '5g Core')
        cfg.commit = ParsingUtils.parse_commit(params, '5g Core')

        cfg.network = Core5GConfigParser._parse_5g_network_config(params)

        return cfg
