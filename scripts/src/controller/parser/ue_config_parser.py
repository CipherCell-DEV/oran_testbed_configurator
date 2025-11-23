import ipaddress
import logging
from typing import List

from controller.parser.parser_utils import ParsingUtils
from model.ue_config import UEFieldIdentifiers, DefaultValuesUE, UECfg, USIMCfg, USIMMode, USIMAlgo, \
    UEGatewayCfg, ALLOWED_IMPLEMENTATION_LIST, UEInstCfg


class UEConfigParser:
    @staticmethod
    def parse_ue_cfg(elements: dict) -> UECfg:
        logging.info("Parse UE Configuration")
        list_cfgs = []
        ue_cfg = UECfg()
        for params in elements['ues']:
            keys = list(params.keys())
            if len(keys) > 1:
                logging.error(f'Expected exactly one UE name per config entry, but found {len(keys)}: {keys}')
            cfg = UEInstCfg()
            cfg.name = keys[0]
            params = params[cfg.name]
            cfg.build_type = ParsingUtils.parse_build_type(params, 'UE')
            cfg.implementation = ParsingUtils.parse_implementation(params, ALLOWED_IMPLEMENTATION_LIST, 'UE')
            cfg.commit = ParsingUtils.parse_commit(params, 'UE')

            if UEFieldIdentifiers.IP_ADDR in params:
                cfg.ip = ipaddress.IPv4Address(params[UEFieldIdentifiers.IP_ADDR])
            else:
                raise KeyError(f"Missing required parameter for UE config: '{UEFieldIdentifiers.IP_ADDR}'")

            if UEFieldIdentifiers.SRATE in params:
                cfg.srate = params[UEFieldIdentifiers.SRATE]
            else:
                logging.warning(
                    f"No srate specified for UE -> Apply default {UEFieldIdentifiers.SRATE} "
                    f"{DefaultValuesUE.DEFAULT_SRATE}")
                cfg.srate = DefaultValuesUE.DEFAULT_SRATE

            if UEFieldIdentifiers.USIM in params:
                cfg.usim = UEConfigParser._parse_usim_cfg(params[UEFieldIdentifiers.USIM])
            else:
                raise KeyError(f"Missing required parameter for UE config: '{UEFieldIdentifiers.USIM}'")

            if UEFieldIdentifiers.GATEWAY in params:
                cfg.gateway = UEConfigParser._parse_ue_gw(params[UEFieldIdentifiers.GATEWAY])

            list_cfgs.append(cfg)

        ue_cfg.ues = list_cfgs

        if UEFieldIdentifiers.IP_RANGE in elements:
            ue_cfg.ip_range = ipaddress.IPv4Network(elements[UEFieldIdentifiers.IP_RANGE])
        else:
            raise KeyError(
                f"Missing required parameter {UEFieldIdentifiers.IP_RANGE}")

        if UEFieldIdentifiers.GATEWAY in elements:
            ue_cfg.gateway = ipaddress.IPv4Address(elements[UEFieldIdentifiers.GATEWAY])
        else:
            raise KeyError(
                f"Missing required parameter {UEFieldIdentifiers.GATEWAY}")

        return ue_cfg

    @staticmethod
    def _parse_usim_cfg(params: dict) -> USIMCfg:
        logging.info("Parse USIM Configuration")
        cfg = USIMCfg()
        if UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE in params:
            if params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE] == 'soft':
                cfg.mode = USIMMode.SOFT
            elif params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE] == 'hard':
                cfg.mode = USIMMode.HARD
            else:
                raise ValueError(f"Unsupported USIM mode: {params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE]}")
        else:
            raise KeyError(
                f"Missing required parameter for USIM config: '{UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.MODE}'")

        if UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO in params:
            if params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == 'milenage':
                cfg.algo = USIMAlgo.MILENAGE
            elif params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == 'xor':
                cfg.algo = USIMAlgo.XOR
            elif params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == 'comp':
                cfg.algo = USIMAlgo.COMP
            elif params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == 'comp128_1':
                cfg.algo = USIMAlgo.COMP128_1
            elif params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == 'comp128_2':
                cfg.algo = USIMAlgo.COMP128_2
            elif params[UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.ALGO] == 'comp128_3':
                cfg.algo = USIMAlgo.COMP128_3
            else:
                raise ValueError(f"Unsupported USIM algorithm: {params['algo']}")

        for key in [UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.OPC,
                    UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.KEY,
                    UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMSI,
                    UEFieldIdentifiers.USIM_FIELD_IDENTIFIERS.IMEI]:
            cfg_value = params.get(key)
            if cfg_value is not None:
                setattr(cfg, key, cfg_value)
            else:
                raise KeyError(f"Missing required parameter for USIM config: '{key}'")

        return cfg

    @staticmethod
    def _parse_ue_gw(params: dict) -> UEGatewayCfg:
        logging.info("Parse USIM Gateway Configuration")
        cfg = UEGatewayCfg()

        if UEFieldIdentifiers.GATEWAY_IDENTIFIERS.NETNS in params:
            cfg.netns = params[UEFieldIdentifiers.GATEWAY_IDENTIFIERS.NETNS]
        else:
            logging.warning("No netns specified for USIM GW -> Apply default netns 'ue1'")
            cfg.netns = DefaultValuesUE.DEFAULT_UE_NETNS

        if UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_DEVNAME in params:
            cfg.ip_devname = params[UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_DEVNAME]
        else:
            logging.warning(
                f"No {UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_DEVNAME} specified for USIM GW -> Apply default "
                f"devname '{DefaultValuesUE.DEFAULT_UE_GW_DEVNAME}'")
            cfg.ip_devname = DefaultValuesUE.DEFAULT_UE_GW_DEVNAME

        if UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_NETMASK in params:
            cfg.ip_netmask = ipaddress.IPv4Network(params[UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_NETMASK])
        else:
            raise KeyError(
                f"Missing required parameter for USIM GW config: '{UEFieldIdentifiers.GATEWAY_IDENTIFIERS.IP_NETMASK}'")

        return cfg
