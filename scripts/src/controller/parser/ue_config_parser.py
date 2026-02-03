"""
UE configuration parsing utilities.

This module provides functionality to parse UE-related configuration
dictionaries into configuration model objects. It handles
validation, default values, and conversion of network- and USIM-related
parameters.
"""

import ipaddress
import logging
from typing import Tuple

from controller.parser.parser_utils import ParsingUtils
from model.setup_configuration import ComponentIdentifiers
from model.ue_config import (
    UEFieldIdentifiers,
    DefaultValuesUE,
    UECfg,
    USIMCfg,
    USIMMode,
    USIMAlgo,
    UEGatewayCfg,
    UEInstCfg,
)


class UEConfigParser:
    """
    Parses and validates UE configuration entries.
    """

    @staticmethod
    def parse_ue_cfg(elements: dict) -> UECfg:
        """
        Turns a dictionary, e.g. parsed from a YAML file into a UECfg object.
        """
        logging.info("Parse UE Configuration")
        list_cfgs = []
        ue_cfg = UECfg()

        if "ues" not in elements:
            raise KeyError("Missing required top-level key: 'ues'")

        for params in elements["ues"]:
            keys = list(params.keys())
            cfg, param = UEConfigParser._parse_general_ue_settings(keys, params)

            if UEFieldIdentifiers.IP_ADDR not in param:
                raise KeyError(
                    f"Missing required parameter for UE config: "
                    f"'{UEFieldIdentifiers.IP_ADDR}'"
                )
            try:
                cfg.ip = ipaddress.IPv4Address(param[UEFieldIdentifiers.IP_ADDR])
            except ValueError as e:
                raise ValueError(f"Invalid UE IP address: {e}") from e

            if UEFieldIdentifiers.SRATE not in param:
                logging.warning(
                    "No srate specified for UE '%s' -> applying default %s",
                    cfg.name,
                    DefaultValuesUE.DEFAULT_SRATE,
                )
                cfg.srate = DefaultValuesUE.DEFAULT_SRATE
            else:
                cfg.srate = param[UEFieldIdentifiers.SRATE]

            cfg.usim = UEConfigParser._parse_usim_cfg(param)

            if UEFieldIdentifiers.GATEWAY in param:
                cfg.gateway = UEConfigParser._parse_ue_gw(
                    param[UEFieldIdentifiers.GATEWAY]
                )

            list_cfgs.append(cfg)

        ue_cfg.ues = list_cfgs

        if "network" in elements:
            ue_cfg = UEConfigParser._parse_network_helper(ue_cfg, elements)
        else:
            raise KeyError("Missing required parameter: 'network'")

        return ue_cfg

    @staticmethod
    def _parse_general_ue_settings(keys, params) -> Tuple[UEInstCfg, dict]:
        """Parse general UE settings, such as name, repository or implementation for a UE."""
        cfg = UEInstCfg()
        if len(keys) < 1:
            raise KeyError("Missing required parameter for UE config")
        if len(keys) != 1:
            raise ValueError(f"Expected exactly one UE name, got {len(keys)}: {keys}")
        cfg.name = keys[0]
        param = params[cfg.name]
        cfg.build_type = ParsingUtils.parse_build_type(
            param, ComponentIdentifiers.CFG_UE
        )
        cfg.implementation = ParsingUtils.parse_implementation(
            param, ComponentIdentifiers.CFG_UE
        )
        cfg.commit = ParsingUtils.parse_commit(param, ComponentIdentifiers.CFG_UE)
        cfg.repository = ParsingUtils.parse_repository(
            param, ComponentIdentifiers.CFG_UE
        )
        return cfg, param

    @staticmethod
    def _parse_usim_cfg(param: dict) -> USIMCfg:
        logging.info("Parse USIM Configuration")
        if UEFieldIdentifiers.USIM not in param:
            raise KeyError(
                f"Missing required parameter for UE config: '{UEFieldIdentifiers.USIM}'"
            )

        usim_param = param[UEFieldIdentifiers.USIM]
        cfg = USIMCfg()
        if UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE in usim_param:
            if usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE] == "soft":
                cfg.mode = USIMMode.SOFT
            elif usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE] == "hard":
                cfg.mode = USIMMode.HARD
            else:
                raise ValueError(
                    f"Unsupported USIM mode: "
                    f"{usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE]}"
                )
        else:
            raise KeyError(
                f"Missing required parameter for USIM config: "
                f"'{UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE}'"
            )

        cfg = UEConfigParser._parse_usim_algo_helper(cfg, usim_param)

        for key in [
            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.OPC,
            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.KEY,
            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMSI,
            UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMEI,
        ]:
            cfg_value = usim_param.get(key)
            if cfg_value is not None:
                setattr(cfg, key, cfg_value)
            else:
                raise KeyError(f"Missing required parameter for USIM config: '{key}'")

        return cfg

    @staticmethod
    def _parse_ue_gw(params: dict) -> UEGatewayCfg:
        logging.info("Parse UE Gateway Configuration")
        cfg = UEGatewayCfg()

        if UEFieldIdentifiers.GATEWAY_IDENTIFIERS.NETNS in params:
            cfg.netns = params[UEFieldIdentifiers.GATEWAY_IDENTIFIERS.NETNS]
        else:
            logging.warning(
                "No netns specified for USIM GW -> Apply default netns 'ue1'"
            )
            cfg.netns = DefaultValuesUE.DEFAULT_UE_NETNS

        if UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_DEVNAME in params:
            cfg.ip_devname = params[UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_DEVNAME]
        else:
            logging.warning(
                "No %s specified for USIM GW -> Apply default device name '%s'",
                UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_DEVNAME,
                DefaultValuesUE.DEFAULT_UE_GW_DEVNAME,
            )
            cfg.ip_devname = DefaultValuesUE.DEFAULT_UE_GW_DEVNAME

        if UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_NETMASK in params:
            try:
                cfg.ip_netmask = ipaddress.IPv4Network(
                    params[UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_NETMASK]
                )
            except ValueError as e:
                raise ValueError(f"Invalid network configuration: {e}") from e
        else:
            raise KeyError(
                f"Missing required parameter for USIM GW config: "
                f"'{UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_NETMASK}'"
            )

        return cfg

    @staticmethod
    def _parse_network_helper(ue_cfg: UECfg, elements: dict) -> UECfg:
        """
        Helper method to parse network configuration.
        """

        if UEFieldIdentifiers.IP_RANGE in elements["network"]:
            try:
                ue_cfg.ip_range = ipaddress.IPv4Network(
                    elements["network"][UEFieldIdentifiers.IP_RANGE]
                )
            except ValueError as e:
                raise ValueError(f"Invalid network configuration: {e}") from e
        else:
            raise KeyError(f"Missing required parameter {UEFieldIdentifiers.IP_RANGE}")

        if UEFieldIdentifiers.GATEWAY not in elements["network"]:
            raise KeyError(f"Missing required parameter {UEFieldIdentifiers.GATEWAY}")
        try:
            ue_cfg.gateway = ipaddress.IPv4Address(
                elements["network"][UEFieldIdentifiers.GATEWAY]
            )
        except ValueError as e:
            raise ValueError(f"Invalid network configuration: {e}") from e
        return ue_cfg

    @staticmethod
    def _parse_usim_algo_helper(cfg: USIMCfg, usim_param: dict) -> USIMCfg:
        """
        Helper function to parse USIM algo config.
        """
        logging.info("Parse USIM Algo Configuration")
        if UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO in usim_param:
            if usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == "milenage":
                cfg.algo = USIMAlgo.MILENAGE
            elif usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == "xor":
                cfg.algo = USIMAlgo.XOR
            elif usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == "comp":
                cfg.algo = USIMAlgo.COMP
            elif (
                usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO]
                == "comp128_1"
            ):
                cfg.algo = USIMAlgo.COMP128_1
            elif (
                usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO]
                == "comp128_2"
            ):
                cfg.algo = USIMAlgo.COMP128_2
            elif (
                usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO]
                == "comp128_3"
            ):
                cfg.algo = USIMAlgo.COMP128_3
            else:
                raise ValueError(
                    f"Unsupported USIM algorithm: "
                    f"{usim_param[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO]}"
                )
        else:
            raise KeyError("USIM algorithm is not specified")
        return cfg
