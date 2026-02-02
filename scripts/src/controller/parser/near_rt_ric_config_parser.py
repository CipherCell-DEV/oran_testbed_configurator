import ipaddress
import logging
from typing import List

from controller.parser.parser_utils import ParsingUtils
from model.ric_config import NearRtRICCFG, RICFieldIdentifiers, RICRelease, DefaultValuesRIC, \
    NearRTRICNetworkConfig, RICImplementation
from model.setup_configuration import GeneralIdentifiers, ComponentIdentifiers


class NearRTRICConfigParser:
    @staticmethod
    def parse_near_rt_ric_cfgs(params: dict) -> List[NearRtRICCFG]:
        """
        Parse the near-RT RIC implementations listed in the near-RT RIC section of the build configuration.
        The network section applies to all near-RT RIC implementations.
        """
        logging.info("Parse near-RT RIC Configuration")
        rics = []

        # All ric vendor implementations share the  same network data
        if RICFieldIdentifiers.NETWORK in params:
            ric_network = NearRTRICConfigParser._parse_network_config(params['network'])
        else:
            ric_network = NearRTRICNetworkConfig()
            logging.warning("No IP address specified -> Apply default network config")
            ric_network.subnet = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['subnet']
            ric_network.dbaas_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['dbaas_ip']
            ric_network.e2term_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['e2term_ip']
            ric_network.e2mgr_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['e2mgr_ip']
            ric_network.submgr_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['submgr_ip']
            ric_network.rtmgr_sim_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['rtmgr_sim_ip']
            ric_network.xapp_runner_ip = DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['xapp_runner_ip']

        # iterate over all implementations
        if GeneralIdentifiers.VENDOR in params:
            for impl in params[GeneralIdentifiers.VENDOR]:
                cfg = NearRtRICCFG()
                cfg.ip_config = ric_network
                cfg.build_type = ParsingUtils.parse_build_type(impl, ComponentIdentifiers.CFG_NEAR_RT_RIC)
                cfg.implementation = ParsingUtils.parse_implementation(impl, ComponentIdentifiers.CFG_NEAR_RT_RIC)
                cfg.commit = ParsingUtils.parse_commit(impl, ComponentIdentifiers.CFG_NEAR_RT_RIC)
                cfg.repository = ParsingUtils.parse_repository(impl, ComponentIdentifiers.CFG_NEAR_RT_RIC)

                if RICFieldIdentifiers.RELEASE in impl:
                    cfg.release = RICRelease.get_version_from_field_identifier(impl[RICFieldIdentifiers.RELEASE])
                else:
                    cfg.release = DefaultValuesRIC.DEFAULT_RELEASE
                    if cfg.implementation is RICImplementation.ORAN_SC_RIC:
                        logging.warning(f"No sc ric release defined use default release {DefaultValuesRIC.DEFAULT_RELEASE}")
                rics.append(cfg)

        if len(rics) == 0:
            logging.warning("No RICs are defined in the build config! Nothing to be built!")
        return rics

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
