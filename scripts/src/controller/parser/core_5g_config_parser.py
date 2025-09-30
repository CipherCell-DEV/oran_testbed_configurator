import ipaddress
import logging

from controller.parser.parser_utils import ParsingUtils
from model.core_config import Core5GCfg, CoreFieldIdentifiers, ALLOWED_IMPLEMENTATION_LIST


class Core5GConfigParser:

    @staticmethod
    def parse_5g_cfg(params: dict) -> Core5GCfg:
        """ Parse the 5G Core Network configuration. """
        logging.info("Parse 5GC Core Configuration")
        cfg = Core5GCfg()

        cfg.build_type = ParsingUtils.parse_build_type(params, '5g Core')
        cfg.implementation = ParsingUtils.parse_implementation(params, ALLOWED_IMPLEMENTATION_LIST, '5g Core')
        cfg.commit = ParsingUtils.parse_commit(params, '5g Core')

        if CoreFieldIdentifiers.IP_ADDR in params:
            cfg.ip = ipaddress.IPv4Address(params[CoreFieldIdentifiers.IP_ADDR])
        else:
            raise KeyError(f"Missing required parameter for 5GC config: '{CoreFieldIdentifiers.IP_ADDR}'")

        if CoreFieldIdentifiers.SUBNET in params:
            cfg.network = ipaddress.IPv4Network(params[CoreFieldIdentifiers.SUBNET])
        else:
            raise KeyError(f"Missing required parameter for 5GC config: '{CoreFieldIdentifiers.SUBNET}'")

        if cfg.ip not in cfg.network:
            raise ValueError(
                f"Configured IP '{cfg.ip}' is not inside the subnet '{cfg.network}'"
            )

        return cfg
