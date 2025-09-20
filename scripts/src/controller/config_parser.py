import os
import ipaddress
import logging
from typing import List
import yaml

from model.core_config import Core5GCfg, CoreImplementation, CoreFieldIdentifiers
from model.gnb_config import GNBIPConfig, GNBCfg, GNBImplementation, GnbFieldIdentifiers, DefaultValuesGNB
from model.ric_config import NearRTRICNetworkConfig, NearRtRICCFG, RICImplementation, RICRelease, DefaultValuesRIC, \
    RICFieldIdentifiers
from model.setup_configuration import EnvironmentCfg, SetupConfiguration, \
    ComponentIdentifiers
from model.ue_config import USIMCfg, USIMMode, USIMAlgo, UEGatewayCfg, UECfg, UEImplementation, DefaultValuesUE, \
    UEFieldIdentifiers
from model.utils_config import BuildType, FILE_DIR


class ConfigParser:
    """ Class to parse the YAML configuration file and populate the SetupConfiguration dataclass."""

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

    @staticmethod
    def _parse_near_rt_ric_cfg(params: dict) -> NearRtRICCFG:
        """ Parse the near-RT RIC configuration. """
        logging.info("Parse near-RT RIC Configuration")
        cfg = NearRtRICCFG()

        if RICFieldIdentifiers.IMPLEMENTATION in params:
            if params[RICFieldIdentifiers.IMPLEMENTATION] == 'oran-sc-ric':
                cfg.type = RICImplementation.ORAN_SC_RIC
            else:
                raise ValueError(f"Unsupported RIC implementation: {params[RICFieldIdentifiers.IMPLEMENTATION]}")
        else:
            raise KeyError("Missing required parameter: 'implementation'")

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
            cfg.ip_config = ConfigParser._parse_network_config(params['network'])
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
    def _parse_5g_cfg(params: dict) -> Core5GCfg:
        """ Parse the 5G Core Network configuration. """
        logging.info("Parse 5GC Core Configuration")
        cfg = Core5GCfg()

        if CoreFieldIdentifiers.IMPLEMENTATION in params:
            if params[CoreFieldIdentifiers.IMPLEMENTATION] == 'srs':
                cfg.implementation = CoreImplementation.SRS
            else:
                raise ValueError(f"Unsupported 5GC type: {params[CoreFieldIdentifiers.IMPLEMENTATION]}")
        else:
            raise KeyError("Missing required parameter for 5GC config: 'type'")

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

    @staticmethod
    def _parse_gnb_cfg(params: dict) -> GNBCfg:
        logging.info("Parse gNB Configuration")
        cfg = GNBCfg()

        if GnbFieldIdentifiers.BUILD_TYPE in params:
            if params[GnbFieldIdentifiers.BUILD_TYPE] == 'docker':
                cfg.build_type = BuildType.DOCKER
            elif params[GnbFieldIdentifiers.BUILD_TYPE] == 'local':
                cfg.build_type = BuildType.NATIVE
            else:
                raise ValueError(f"Unsupported build type: {params['build_type']}")
        else:
            raise KeyError("Missing required parameter for gNB config: 'build_type'")

        if GnbFieldIdentifiers.GNB_TYPE in params:
            if params[GnbFieldIdentifiers.GNB_TYPE] == 'srs':
                cfg.type = GNBImplementation.SRS
            else:
                raise ValueError(f"Unsupported gNB type: {params[GnbFieldIdentifiers.GNB_TYPE]}")
        else:
            raise KeyError(f"Missing required parameter for gNB config: '{GnbFieldIdentifiers.GNB_TYPE}'")

        if GnbFieldIdentifiers.IP_ADDR in params:
            cfg.ip_config = ConfigParser._parse_gnb_ip_config(params[GnbFieldIdentifiers.IP_ADDR])
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

    @staticmethod
    def _parse_ue_cfg(elements: dict) -> List[UECfg]:
        logging.info("Parse UE Configuration")
        list_cfgs = []
        for params in elements:
            cfg = UECfg()

            if UEFieldIdentifiers.IMPLEMENTATION in params:
                if params[UEFieldIdentifiers.IMPLEMENTATION] == 'srs':
                    cfg.implementation = UEImplementation.SRS_4G
                else:
                    raise ValueError(f"Unsupported ue implementation: {params[UEFieldIdentifiers.IMPLEMENTATION]}")
            else:
                raise KeyError(f"Missing required parameter '{UEFieldIdentifiers.IMPLEMENTATION}'")

            if UEFieldIdentifiers.BUILD_TYPE in params:
                if params[UEFieldIdentifiers.BUILD_TYPE] == 'docker':
                    cfg.build_type = BuildType.DOCKER
                elif params[UEFieldIdentifiers.BUILD_TYPE] == 'local':
                    cfg.build_type = BuildType.NATIVE
                else:
                    raise ValueError(f"Unsupported build type: {params[UEFieldIdentifiers.BUILD_TYPE]}")
            else:
                raise KeyError(f"Missing required parameter for UE config: '{UEFieldIdentifiers.BUILD_TYPE}'")

            if UEFieldIdentifiers.NAME in params:
                cfg.name = params[UEFieldIdentifiers.NAME]
            else:
                raise KeyError(f"Missing required parameter for UE config: '{UEFieldIdentifiers.NAME}'")

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
                cfg.usim = ConfigParser._parse_usim_cfg(params[UEFieldIdentifiers.USIM])
            else:
                raise KeyError(f"Missing required parameter for UE config: '{UEFieldIdentifiers.USIM}'")

            if UEFieldIdentifiers.GATEWAY in params:
                cfg.gateway = ConfigParser._parse_ue_gw(params[UEFieldIdentifiers.GATEWAY])

            list_cfgs.append(cfg)

        return list_cfgs

    @staticmethod
    def _parse_environment_cfg(params: dict) -> EnvironmentCfg:
        logging.info("Parse Environment Configuration")
        cfg = EnvironmentCfg()

        if 'build_type' in params:
            if params['build_type'] == 'local':
                cfg.build_type = BuildType.NATIVE
            elif params['build_type'] == 'docker':
                cfg.build_type = BuildType.DOCKER
            else:
                raise ValueError(f"Unsupported build type: {params['build_type']}")
        else:
            raise KeyError("Missing required parameter for Environment config: 'build_type'")

        if 'log_level' in params:
            if params['log_level'] in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
                cfg.log_level = params['log_level']
            else:
                raise ValueError(f"Unsupported log level: {params['log_level']}")
        else:
            logging.warning("No log level specified -> Apply default log level 'INFO'")
            cfg.log_level = 'INFO'

        if 'log_dir' in params:
            cfg.log_dir = os.path.join(FILE_DIR, '../..', params['log_dir'])
        else:
            logging.warning("No log directory specified -> Logging to console only")

        if 'build_dir' in params:
            cfg.build_dir = os.path.join(FILE_DIR, '../..', params['build_dir'])
        else:
            raise KeyError("Missing required parameter for Environment config: 'build_dir'")

        return cfg

    @staticmethod
    def parse_config_file(file_path: str) -> SetupConfiguration:
        setup_config = SetupConfiguration()

        with open(file_path, "r") as f:
            parsed_config = yaml.safe_load(f)
            for config_entry in parsed_config:
                if config_entry == ComponentIdentifiers.CFG_NEAR_RT_RIC:
                    setup_config.near_rt_ric = ConfigParser._parse_near_rt_ric_cfg(
                        parsed_config[ComponentIdentifiers.CFG_NEAR_RT_RIC])
                elif config_entry == ComponentIdentifiers.CFG_5GC:
                    setup_config.core_5g = ConfigParser._parse_5g_cfg(parsed_config[ComponentIdentifiers.CFG_5GC])
                elif config_entry == ComponentIdentifiers.CFG_UE:
                    setup_config.ue = ConfigParser._parse_ue_cfg(parsed_config[ComponentIdentifiers.CFG_UE])
                elif config_entry == ComponentIdentifiers.CFG_GNB:
                    setup_config.gnb = ConfigParser._parse_gnb_cfg(parsed_config[ComponentIdentifiers.CFG_GNB])
                elif config_entry == ComponentIdentifiers.CFG_ENVIRONMENT:
                    setup_config.environment = ConfigParser._parse_environment_cfg(
                        parsed_config[ComponentIdentifiers.CFG_ENVIRONMENT])
                else:
                    raise KeyError(f"Unknown configuration section: '{config_entry}'")

        return setup_config
