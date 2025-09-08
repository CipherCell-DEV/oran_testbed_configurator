import os
import ipaddress
import logging
from typing import List

import yaml

from scripts.src.model.setup_configuration import SetupConfiguration, Core5GCfg, GNBCfg, UECfg, NearRtRICCFG, \
    RICImplementation, RICRelease, NearRTRICNetworkConfig, USIMCfg, USIMMode, USIMAlgo, GNBType, GNBIPConfig, \
    EnvironmentCfg, BuildType, UEGatewayCfg, CoreImplementation, DefaultValues, ComponentIdentifiers, FieldIdentifiers, \
    UEImplementation


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

        if 'implementation' in params:
            if params['implementation'] == 'oran-sc-ric':
                cfg.type = RICImplementation.ORAN_SC_RIC
            else:
                raise ValueError(f"Unsupported RIC implementation: {params['implementation']}")
        else:
            raise KeyError("Missing required parameter: 'implementation'")

        if 'release' in params:
            if params['release'] == 'i':
                cfg.release = RICRelease.RELEASE_i
            elif params['release'] == 'l':
                cfg.release = RICRelease.RELEASE_l
            else:
                raise ValueError(f"Unsupported Release: {params['release']}")
        else:
            cfg.release = DefaultValues.DEFAULT_RELEASE
            logging.warning(f"No sc ric release defined use default release i")

        if 'network' in params:
            cfg.ip_config = ConfigParser._parse_network_config(params['network'])
        else:
            logging.warning("No IP address specified -> Apply default network config")
            cfg.ip_config = NearRTRICNetworkConfig()
            cfg.ip_config.subnet = ipaddress.IPv4Network('10.0.2.0/24')
            cfg.ip_config.dbaas_ip = ipaddress.IPv4Address('10.0.2.12')
            cfg.ip_config.e2term_ip = ipaddress.IPv4Address('10.0.2.10')
            cfg.ip_config.e2mgr_ip = ipaddress.IPv4Address('10.0.2.11')
            cfg.ip_config.submgr_ip = ipaddress.IPv4Address('10.0.2.14')
            cfg.ip_config.rtmgr_sim_ip = ipaddress.IPv4Address('10.0.2.15')
            cfg.ip_config.xapp_runner_ip = ipaddress.IPv4Address('10.0.2.20')

        return cfg

    @staticmethod
    def _parse_5g_cfg(params: dict) -> Core5GCfg:
        """ Parse the 5G Core Network configuration. """
        logging.info("Parse 5GC Core Configuration")
        cfg = Core5GCfg()

        if 'implementation' in params:
            if params['implementation'] == 'srs':
                cfg.implementation = CoreImplementation.SRS
            else:
                raise ValueError(f"Unsupported 5GC type: {params['type']}")
        else:
            raise KeyError("Missing required parameter for 5GC config: 'type'")

        if 'ip_addr' in params:
            cfg.ip = ipaddress.IPv4Address(params['ip_addr'])
        else:
            raise KeyError("Missing required parameter for 5GC config: 'ip'")

        if 'subnet' in params:
            cfg.network = ipaddress.IPv4Network(params['subnet'])
        else:
            raise KeyError("Missing required parameter for 5GC config: 'subnet'")

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

        if FieldIdentifiers.BUILD_TYPE in params:
            if params[FieldIdentifiers.BUILD_TYPE] == 'docker':
                cfg.build_type = BuildType.DOCKER
            elif params[FieldIdentifiers.BUILD_TYPE] == 'local':
                cfg.build_type = BuildType.LOCAL
            else:
                raise ValueError(f"Unsupported build type: {params['build_type']}")
        else:
            raise KeyError("Missing required parameter for gNB config: 'build_type'")

        if FieldIdentifiers.GNB_TYPE in params:
            if params[FieldIdentifiers.GNB_TYPE] == 'srs':
                cfg.type = GNBType.SRS
            else:
                raise ValueError(f"Unsupported gNB type: {params['type']}")
        else:
            raise KeyError("Missing required parameter for gNB config: 'type'")

        if FieldIdentifiers.IP_ADDR in params:
            cfg.ip_config = ConfigParser._parse_gnb_ip_config(params[FieldIdentifiers.IP_ADDR])
        else:
            raise KeyError("Missing required parameter for gNB config: 'ip_addr'")

        if FieldIdentifiers.SRATE in params:
            cfg.srate = params[FieldIdentifiers.SRATE]
        else:
            logging.warning("No srate specified for gNB -> Apply default srate 11.52e6")
            cfg.srate = DefaultValues.DEFAULT_SRATE

        if FieldIdentifiers.TX_GAIN in params:
            cfg.tx_gain = params[FieldIdentifiers.TX_GAIN]
        else:
            logging.warning("No tx_gain specified for gNB -> Apply default tx_gain 75")
            cfg.tx_gain = 75

        if FieldIdentifiers.RX_GAIN in params:
            cfg.rx_gain = params[FieldIdentifiers.RX_GAIN]
        else:
            logging.warning("No rx_gain specified for gNB -> Apply default rx_gain 75")
            cfg.rx_gain = 75

        return cfg

    @staticmethod
    def _parse_usim_cfg(params: dict) -> USIMCfg:
        logging.info("Parse USIM Configuration")
        cfg = USIMCfg()
        if 'mode' in params:
            if params['mode'] == 'soft':
                cfg.mode = USIMMode.SOFT
            elif params['mode'] == 'hard':
                cfg.mode = USIMMode.HARD
            else:
                raise ValueError(f"Unsupported USIM mode: {params['mode']}")
        else:
            raise KeyError("Missing required parameter for USIM config: 'mode'")

        if 'algo' in params:
            if params['algo'] == 'milenage':
                cfg.algo = USIMAlgo.MILENAGE
            elif params['algo'] == 'xor':
                cfg.algo = USIMAlgo.XOR
            elif params['algo'] == 'comp':
                cfg.algo = USIMAlgo.COMP
            elif params['algo'] == 'comp128_1':
                cfg.algo = USIMAlgo.COMP128_1
            elif params['algo'] == 'comp128_2':
                cfg.algo = USIMAlgo.COMP128_2
            elif params['algo'] == 'comp128_3':
                cfg.algo = USIMAlgo.COMP128_3
            else:
                raise ValueError(f"Unsupported USIM algorithm: {params['algo']}")

        for key in ['opc', 'k', 'imsi', 'imei']:
            cfg_value = params.get(key)
            if cfg_value is not None:
                setattr(cfg, key, cfg_value)
            else:
                raise KeyError(f"Missing required parameter for USIM config: '{key}'")

        return cfg

    @staticmethod
    def _parse_usim_gw(params: dict) -> UEGatewayCfg:
        logging.info("Parse USIM Gateway Configuration")
        cfg = UEGatewayCfg()

        if 'netns' in params:
            cfg.netns = params['netns']
        else:
            logging.warning("No netns specified for USIM GW -> Apply default netns 'ue1'")
            cfg.netns = DefaultValues.DEFAULT_UE_NETNS

        if 'ip_devname' in params:
            cfg.ip_devname = params['ip_devname']
        else:
            logging.warning("No ip_devname specified for USIM GW -> Apply default devname 'tun_srsue'")
            cfg.ip_devname = DefaultValues.DEFAULT_UE_GW_DEVNAME

        if 'ip_netmask' in params:
            cfg.ip_netmask = ipaddress.IPv4Network(params['ip_netmask'])
        else:
            raise KeyError("Missing required parameter for USIM GW config: 'ip_netmask'")

        return cfg

    @staticmethod
    def _parse_ue_cfg(elements: dict) -> List[UECfg]:
        logging.info("Parse UE Configuration")
        list_cfgs = []
        for params in elements:
            cfg = UECfg()

            if 'implementation' in params:
                if params['implementation'] == 'srs':
                    cfg.implementation = UEImplementation.SRS_4G
                else:
                    raise ValueError(f"Unsupported ue implementation: {params['implementation']}")
            else:
                raise KeyError("Missing required parameter for USIM GW config: 'ip_netmask'")

            if 'build_type' in params:
                if params['build_type'] == 'docker':
                    cfg.build_type = BuildType.DOCKER
                elif params['build_type'] == 'local':
                    cfg.build_type = BuildType.LOCAL
                else:
                    raise ValueError(f"Unsupported build type: {params['build_type']}")
            else:
                raise KeyError("Missing required parameter for UE config: 'build_type'")

            if 'name' in params:
                cfg.name = params['name']
            else:
                raise KeyError("Missing required parameter for UE config: 'name'")

            if 'ip_addr' in params:
                cfg.ip = ipaddress.IPv4Address(params['ip_addr'])
            else:
                raise KeyError("Missing required parameter for UE config: 'ip_addr'")

            if 'srate' in params:
                cfg.srate = params['srate']
            else:
                logging.warning("No srate specified for UE -> Apply default srate 11.52e6")
                cfg.srate = DefaultValues.DEFAULT_SRATE

            if 'usim' in params:
                cfg.usim = ConfigParser._parse_usim_cfg(params['usim'])
            else:
                raise KeyError("Missing required parameter for UE config: 'usim'")

            if 'gateway' in params:
                cfg.gateway = ConfigParser._parse_usim_gw(params['gateway'])

            list_cfgs.append(cfg)

        return list_cfgs

    @staticmethod
    def _parse_environment_cfg(params: dict) -> EnvironmentCfg:
        logging.info("Parse Environment Configuration")
        cfg = EnvironmentCfg()

        if 'build_type' in params:
            if params['build_type'] == 'local':
                cfg.build_type = BuildType.LOCAL
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
            cfg.log_dir = params['log_dir']
        else:
            logging.warning("No log directory specified -> Logging to console only")

        if 'build_dir' in params:
            cfg.build_dir = params['build_dir']
        else:
            raise KeyError("Missing required parameter for Environment config: 'build_dir'")

        return cfg

    @staticmethod
    def parse_config_file(path: str, cfg_file: str) -> SetupConfiguration:
        file_path = os.path.join(path, cfg_file)

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
