"""
Parsers for loading and translating YAML-based configuration files into
internal configuration models used by the system.
"""
import logging
import os

import yaml

from controller.parser.core_5g_config_parser import Core5GConfigParser
from controller.parser.gnb_config_parser import GNBConfigParser
from controller.parser.near_rt_ric_config_parser import NearRTRICConfigParser
from controller.parser.program_config_parser import ProgramConfigParser
from controller.parser.ue_config_parser import UEConfigParser
from controller.parser.zmq_proxy_parser import ZMQProxyParser
from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.program_descr_config import ProgramDescriptionCfg
from model.ric_config import RICImplementation
from model.setup_configuration import EnvironmentCfg, SetupConfiguration, ComponentIdentifiers
from model.utils_config import FILE_DIR, LogLevel


class ConfigParser:
    """ Class to parse the YAML configuration file and populate the SetupConfiguration dataclass."""

    @staticmethod
    def _parse_environment_cfg(params: dict) -> EnvironmentCfg:
        """
        Parses environment definitions such as log levels, build directories, and log directories.
        """
        logging.info("Parse Environment Configuration")
        cfg = EnvironmentCfg()

        def parse_component_implementation(identifier: str, implementation):
            if identifier in params:
                for element in implementation:
                    if element.value == params[identifier]:
                        return element
                raise ValueError(
                    f"Invalid {identifier.replace('_', ' ')} {params[identifier]}"
                )
            logging.warning("No %s identified", identifier.replace("_", " "))
            return None

        cfg.core_implementation = parse_component_implementation(
            'core_implementation', CoreImplementation)
        cfg.gnb_implementation = parse_component_implementation(
            'gnb_implementation', GNBImplementation)
        cfg.ric_implementation = parse_component_implementation(
            'ric_implementation', RICImplementation)

        if 'log_level' in params:
            if params['log_level'] in LogLevel.values():
                cfg.log_level = params['log_level']
            else:
                raise ValueError(f"Unsupported log level: {params['log_level']}")
        else:
            logging.warning("No log level specified -> Apply default log level 'INFO'")
            cfg.log_level = 'INFO'

        if 'log_dir' in params:
            cfg.log_dir = os.path.join(FILE_DIR, '..', params['log_dir'])
        else:
            logging.warning("No log directory specified -> Logging to console only")

        if 'build_dir' in params:
            cfg.build_dir = os.path.join(FILE_DIR, '..', params['build_dir'])
        else:
            raise KeyError("Missing required parameter for Environment config: 'build_dir'")

        if 'docker_registry' in params:
            cfg.docker_registry = params["docker_registry"]

        if 'tag_appendix' in params:
            cfg.tag_appendix = params["tag_appendix"]

        if 'push_local_images' in params:
            cfg.push_local_images = params["push_local_images"]

        return cfg

    @staticmethod
    def parse_config_file(file_path: str) -> SetupConfiguration:
        """
        Loads and parses a YAML setup configuration file, converting each
        configuration section into its corresponding configuration object.
        """
        setup_config = SetupConfiguration()

        with open(file_path, "r", encoding="utf-8") as f:
            parsed_config = yaml.safe_load(f)
            for config_entry in parsed_config:
                match config_entry:
                    case ComponentIdentifiers.CFG_NEAR_RT_RIC.value:
                        setup_config.near_rt_rics = NearRTRICConfigParser.parse_near_rt_ric_cfgs(
                            parsed_config[ComponentIdentifiers.CFG_NEAR_RT_RIC.value])

                    case ComponentIdentifiers.CFG_5GC.value:
                        setup_config.cores_5g = Core5GConfigParser.parse_5g_cfgs(
                            parsed_config[ComponentIdentifiers.CFG_5GC.value])

                    case ComponentIdentifiers.CFG_UE.value:
                        setup_config.ue = UEConfigParser.parse_ue_cfg(
                            parsed_config[ComponentIdentifiers.CFG_UE.value])

                    case ComponentIdentifiers.CFG_GNB.value:
                        setup_config.gnbs = GNBConfigParser.parse_gnb_cfgs(
                            parsed_config[ComponentIdentifiers.CFG_GNB.value])

                    case ComponentIdentifiers.CFG_ZMQ_PROXY.value:
                        setup_config.zmq_proxy = ZMQProxyParser.parse_zmq_proxy_cfg(
                            parsed_config[ComponentIdentifiers.CFG_ZMQ_PROXY.value])

                    case ComponentIdentifiers.CFG_ENVIRONMENT.value:
                        setup_config.environment = ConfigParser._parse_environment_cfg(
                            parsed_config[ComponentIdentifiers.CFG_ENVIRONMENT.value])

                    case _:
                        raise KeyError(f"Unknown configuration section: '{config_entry}'")

        return setup_config

    @staticmethod
    def parse_program_setup_config(file_path: str, env_build_path: str) -> ProgramDescriptionCfg:
        """Parses the yaml demo file, which lists a set of programs to be executed.
        Each program may have a specified working directory.
        In case the working directory is not specified, the environment build path is used instead.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            parsed_config = yaml.safe_load(f)
            program_config = ProgramConfigParser.parse_program_cfg(file_path, parsed_config,
                                                                   env_build_path)
            if not program_config.check_validity():
                logging.error("Failed to validate program setup configuration")
            return program_config
