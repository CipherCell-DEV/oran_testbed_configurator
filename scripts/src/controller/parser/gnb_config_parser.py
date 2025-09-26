import ipaddress
import logging

from controller.parser.parser_utils import ParsingUtils
from model.gnb_config import GNBCfg, GnbFieldIdentifiers, DefaultValuesGNB, GNBIPConfig, \
    ALLOWED_IMPLEMENTATION_LIST


class GNBConfigParser:
    @staticmethod
    def parse_gnb_cfg(params: dict) -> GNBCfg:
        logging.info("Parse gNB Configuration")
        cfg = GNBCfg()

        cfg.build_type = ParsingUtils.parse_build_type(params, 'gNB')
        cfg.implementation = ParsingUtils.parse_implementation(params, ALLOWED_IMPLEMENTATION_LIST, 'gNB')

        if GnbFieldIdentifiers.IP_ADDR in params:
            cfg.ip_config = GNBConfigParser._parse_gnb_ip_config(params[GnbFieldIdentifiers.IP_ADDR])
        else:
            raise KeyError(f"Missing required parameter for gNB config: '{GnbFieldIdentifiers.IP_ADDR}'")

        if GnbFieldIdentifiers.SRATE in params:
            cfg.srate = params[GnbFieldIdentifiers.SRATE]
        else:
            logging.warning(f"No srate specified for gNB -> Apply default srate {DefaultValuesGNB.DEFAULT_SRATE}")
            cfg.srate = DefaultValuesGNB.DEFAULT_SRATE

        if GnbFieldIdentifiers.TX_GAIN in params:
            cfg.tx_gain = params[GnbFieldIdentifiers.TX_GAIN]
        else:
            logging.warning(f"No tx_gain specified for gNB -> Apply default tx_gain '{DefaultValuesGNB.TX_GAIN}'")
            cfg.tx_gain = DefaultValuesGNB.TX_GAIN

        if GnbFieldIdentifiers.RX_GAIN in params:
            cfg.rx_gain = params[GnbFieldIdentifiers.RX_GAIN]
        else:
            logging.warning(f"No rx_gain specified for gNB -> Apply default rx_gain '{DefaultValuesGNB.RX_GAIN}'")
            cfg.rx_gain = DefaultValuesGNB.RX_GAIN

        return cfg

    @staticmethod
    def _parse_gnb_ip_config(params: dict) -> GNBIPConfig:
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
