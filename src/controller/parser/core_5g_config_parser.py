"""
Parsing utilities for translating 5G core configuration data into
structured configuration objects.
"""

import ipaddress
import logging
from typing import List

from controller.parser.parser_utils import ParsingUtils
from model.core_config import Core5GCfg, CoreFieldIdentifiers, Core5GNetworkCfg
from model.setup_configuration import GeneralIdentifiers, ComponentIdentifiers


class Core5GConfigParser:
    """Handles parsing and validation of 5G core configuration data."""

    @staticmethod
    def _parse_5g_network_config(params: dict) -> Core5GNetworkCfg:
        if CoreFieldIdentifiers.NETWORK not in params:
            raise KeyError(f"Missing required parameter for 5GC config: "
                           f"'{CoreFieldIdentifiers.NETWORK}'")

        network_cfg = params[CoreFieldIdentifiers.NETWORK]
        core_network = Core5GNetworkCfg()

        field_map = {
            "ip": (CoreFieldIdentifiers.CORE_IP, ipaddress.IPv4Address,
                   "No IP address specified for 5G core"),
            "subnet": (CoreFieldIdentifiers.SUBNET, ipaddress.IPv4Network,
                       "No subnet specified for 5G core"),
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
    def parse_5g_cfgs(params: dict) -> List[Core5GCfg]:
        """
        Parse the 5G Cores implementations listed in the 5gc section of the build configuration.
        The network section applies to all Core implementations.
        """
        logging.info("Parse 5GC Core Configurations")

        # All cores share use the same network data
        network = Core5GConfigParser._parse_5g_network_config(params)

        cores = []

        if GeneralIdentifiers.VENDOR in params:
            for impl in params[GeneralIdentifiers.VENDOR]:
                cfg = Core5GCfg()
                cfg.network = network
                cfg.build_type = ParsingUtils.parse_build_type(impl, ComponentIdentifiers.CFG_5GC)
                cfg.implementation = ParsingUtils.parse_implementation(impl,
                                                                       ComponentIdentifiers.CFG_5GC)
                cfg.commit = ParsingUtils.parse_commit(impl, ComponentIdentifiers.CFG_5GC)
                cfg.repository = ParsingUtils.parse_repository(impl, ComponentIdentifiers.CFG_5GC)
                cores.append(cfg)

        if len(cores) == 0:
            logging.warning("No 5G Cores are defined in the build config! Nothing to be built!")
        return cores
