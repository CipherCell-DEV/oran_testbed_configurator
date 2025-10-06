import ipaddress
import logging

from controller.parser.parser_utils import ParsingUtils
from model.ric_config import NearRtRICCFG, RICFieldIdentifiers, RICRelease, DefaultValuesRIC, \
    NearRTRICNetworkConfig, ALLOWED_IMPLEMENTATION_LIST


class NearRTRICConfigParser:
    @staticmethod
    def parse_near_rt_ric_cfg(params: dict) -> NearRtRICCFG:
        """ Parse the near-RT RIC configuration. """
        logging.info("Parse near-RT RIC Configuration")
        cfg = NearRtRICCFG()

        cfg.build_type = ParsingUtils.parse_build_type(params, 'Near-RT RIC')
        cfg.implementation = ParsingUtils.parse_implementation(params, ALLOWED_IMPLEMENTATION_LIST, 'Near-RT RIC')
        cfg.commit = ParsingUtils.parse_commit(params, 'Near-RT RIC')

        if RICFieldIdentifiers.RELEASE in params:
            if params[RICFieldIdentifiers.RELEASE] == 'i':
                cfg.release = RICRelease.RELEASE_i
            elif params[RICFieldIdentifiers.RELEASE] == 'l':
                cfg.release = RICRelease.RELEASE_l
            else:
                raise ValueError(f"Unsupported Release: {params[RICFieldIdentifiers.RELEASE]}")
        else:
            cfg.release = DefaultValuesRIC.DEFAULT_RELEASE
            logging.warning(f"No sc ric release defined use default release i")

        if RICFieldIdentifiers.NETWORK in params:
            cfg.ip_config = NearRTRICConfigParser._parse_network_config(params['network'])
        else:
            logging.warning("No IP address specified -> Apply default network config")
            cfg.ip_config = NearRTRICNetworkConfig()
            cfg.ip_config.subnet = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['subnet']
            cfg.ip_config.dbaas_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['dbaas_ip']
            cfg.ip_config.e2term_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['e2term_ip']
            cfg.ip_config.e2mgr_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['e2mgr_ip']
            cfg.ip_config.submgr_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['submgr_ip']
            cfg.ip_config.rtmgr_sim_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['rtmgr_sim_ip']
            cfg.ip_config.xapp_runner_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['xapp_runner_ip']

        return cfg

    @staticmethod
    def _parse_network_config(ip_config: dict) -> NearRTRICNetworkConfig:
        """ Parse the network configuration for near-RT RIC. """
        logging.info("Parse near-RT RIC Network Configuration")
        ip_cfg = NearRTRICNetworkConfig()

        # Required subnet
        if "subnet" not in ip_config:
            raise KeyError("Missing required parameter for near-RT RIC IP config: 'subnet'")
        ip_cfg.subnet = ipaddress.IPv4Network(ip_config["subnet"])
        logging.info(f"Configured subnet: {ip_cfg.subnet}")

        # Mapping of config keys to class attributes
        ip_mappings = {
            "dbaas_ip": "dbaas_ip",
            "e2term_ip": "e2term_ip",
            "e2mgr_ip": "e2mgr_ip",
            "submgr_ip": "submgr_ip",
            "appmgr_ip": "appmgr_ip",
            "rtmgr_sim_ip": "rtmgr_sim_ip",
            "xapp_runner_ip": "xapp_runner_ip",
        }

        for cfg_key, attr in ip_mappings.items():
            if cfg_key not in ip_config:
                raise KeyError(
                    f"Missing required parameter for near-RT RIC IP config: '{cfg_key}'"
                )

            # Verify that the IP is within the subnet
            ip = ipaddress.IPv4Address(ip_config[cfg_key])
            if ip not in ip_cfg.subnet:
                raise ValueError(
                    f"IP '{ip}' for '{cfg_key}' is not in the configured subnet '{ip_cfg.subnet}'"
                )

            setattr(ip_cfg, attr, ipaddress.IPv4Address(ip_config[cfg_key]))
            logging.info(f"Configured {attr}: {getattr(ip_cfg, attr)}")

        return ip_cfg
