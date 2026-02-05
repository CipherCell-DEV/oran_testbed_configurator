"""Module for parsing gNB configuration parameters into structured data models."""

import ipaddress
import logging
from typing import List

from controller.parser.parser_utils import ParsingUtils
from model.gnb_config import GNBCfg, GnbFieldIdentifiers, DefaultValuesGNB, GNBIPConfig
from model.setup_configuration import GeneralIdentifiers, ComponentIdentifiers


class GNBConfigParser:
    """
    Provides static methods to parse, validate, and convert raw gNB configuration
    parameters into GNBCfg model instances.
    """

    @staticmethod
    def parse_gnb_cfgs(params: dict) -> List[GNBCfg]:
        """
        Parse gNB network and vendor settings from the given parameters into GNBCfg instances.
        Applies defaults for missing optional fields.
        """

        logging.info("Parse gNB Configuration")

        gnbs = []

        if GnbFieldIdentifiers.NETWORK in params:
            network = GNBConfigParser._parse_gnb_network(params[GnbFieldIdentifiers.NETWORK])
        else:
            raise KeyError(f"Missing required parameter for gNB config: "
                           f"'{GnbFieldIdentifiers.NETWORK}'")

        if GeneralIdentifiers.VENDOR in params:
            for impl in params[GeneralIdentifiers.VENDOR]:
                cfg = GNBCfg()
                cfg.ip_config = network
                cfg.build_type = ParsingUtils.parse_build_type(impl,
                                                               ComponentIdentifiers.CFG_GNB)
                cfg.implementation = ParsingUtils.parse_implementation(impl,
                                                                       ComponentIdentifiers.CFG_GNB)
                cfg.commit = ParsingUtils.parse_commit(impl, ComponentIdentifiers.CFG_GNB)
                cfg.repository = ParsingUtils.parse_repository(impl, ComponentIdentifiers.CFG_GNB)

                if GnbFieldIdentifiers.SRATE in impl:
                    cfg.srate = GNBConfigParser._convert_srate(impl[GnbFieldIdentifiers.SRATE])
                else:
                    logging.warning(
                        "No srate specified for gNB -> Apply default srate %s",
                        DefaultValuesGNB.DEFAULT_SRATE)
                    cfg.srate = DefaultValuesGNB.DEFAULT_SRATE

                if GnbFieldIdentifiers.TX_GAIN in impl:
                    cfg.tx_gain = impl[GnbFieldIdentifiers.TX_GAIN]
                else:
                    logging.warning(
                        "No tx_gain specified for gNB -> Apply default tx_gain: %d",
                        DefaultValuesGNB.TX_GAIN)
                    cfg.tx_gain = DefaultValuesGNB.TX_GAIN

                if GnbFieldIdentifiers.RX_GAIN in impl:
                    cfg.rx_gain = impl[GnbFieldIdentifiers.RX_GAIN]
                else:
                    logging.warning(
                        "No rx_gain specified for gNB -> Apply default rx_gain: %d",
                        DefaultValuesGNB.RX_GAIN)
                    cfg.rx_gain = DefaultValuesGNB.RX_GAIN

                gnbs.append(cfg)

        if len(gnbs) == 0:
            logging.warning("No gNBs found in build configuration. Nothing to be built!")
        return gnbs

    @staticmethod
    def _convert_srate(srate: int) -> float:
        return float(srate) / 1e6

    @staticmethod
    def _parse_gnb_network(params: dict) -> GNBIPConfig:
        cfg = GNBIPConfig()

        def set_ip(p: dict, k: str):
            if k not in p:
                raise KeyError(f"Missing required parameter for gNB IP config: '{k}'")
            return ipaddress.IPv4Address(p[k])

        interfaces_dict = {
            "e2": "e2",
            "ru_sdr": "ru_sdr",
            "cu_cp": "cu_cp",
        }

        for param_key, attr_name in interfaces_dict.items():
            setattr(cfg, attr_name, set_ip(params, param_key))

        return cfg
