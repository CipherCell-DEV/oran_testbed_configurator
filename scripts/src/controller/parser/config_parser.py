import logging
import os

import yaml

from controller.parser.core_5g_config_parser import Core5GConfigParser
from controller.parser.gnb_config_parser import GNBConfigParser
from controller.parser.near_rt_ric_config_parser import NearRTRICConfigParser
from controller.parser.ue_config_parser import UEConfigParser
from model.program_descr_config import ProgramDescriptionCfg
from model.setup_configuration import EnvironmentCfg, SetupConfiguration, \
    ComponentIdentifiers
from model.utils_config import FILE_DIR
from controller.parser.program_config_parser import ProgramConfigParser


class ConfigParser:
    """ Class to parse the YAML configuration file and populate the SetupConfiguration dataclass."""

    @staticmethod
    def _parse_environment_cfg(params: dict) -> EnvironmentCfg:
        """
        Parses environment definitions such as log levels, build directories, and log directories.
        """
        logging.info("Parse Environment Configuration")
        cfg = EnvironmentCfg()

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

        if 'docker_registry' in params:
            cfg.docker_registry = params["docker_registry"]

        if 'tag_appendix' in params:
            cfg.tag_appendix = params["tag_appendix"]

        if 'push_local_images' in params:
            cfg.push_local_images = params["push_local_images"]

        return cfg

    @staticmethod
    def parse_config_file(file_path: str) -> SetupConfiguration:
        setup_config = SetupConfiguration()

        with open(file_path, "r") as f:
            parsed_config = yaml.safe_load(f)
            for config_entry in parsed_config:
                if config_entry == ComponentIdentifiers.CFG_NEAR_RT_RIC:
                    setup_config.near_rt_ric = NearRTRICConfigParser.parse_near_rt_ric_cfg(
                        parsed_config[ComponentIdentifiers.CFG_NEAR_RT_RIC])
                elif config_entry == ComponentIdentifiers.CFG_5GC:
                    setup_config.core_5g = Core5GConfigParser.parse_5g_cfg(parsed_config[ComponentIdentifiers.CFG_5GC])
                elif config_entry == ComponentIdentifiers.CFG_UE:
                    setup_config.ue = UEConfigParser.parse_ue_cfg(parsed_config[ComponentIdentifiers.CFG_UE])
                elif config_entry == ComponentIdentifiers.CFG_GNB:
                    setup_config.gnb = GNBConfigParser.parse_gnb_cfg(parsed_config[ComponentIdentifiers.CFG_GNB])
                elif config_entry == ComponentIdentifiers.CFG_ENVIRONMENT:
                    setup_config.environment = ConfigParser._parse_environment_cfg(
                        parsed_config[ComponentIdentifiers.CFG_ENVIRONMENT])
                else:
                    raise KeyError(f"Unknown configuration section: '{config_entry}'")

        return setup_config

    @staticmethod
    def parse_program_setup_config(file_path: str, env_build_path: str) -> ProgramDescriptionCfg:
        """Parses the yaml demo file, which lists a set of programs to be executed.
        Each program may have a specified working directory.
        In case the working directory is not specified, the environment build path is used instead.
        """
        with open(file_path, "r") as f:
            parsed_config = yaml.safe_load(f)
            program_config = ProgramConfigParser.parse_program_cfg(file_path, parsed_config, env_build_path)
            if not program_config.check_validity():
                logging.error("Failed to validate program setup configuration")
            return program_config
