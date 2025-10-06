import logging

from demo_config import DemoAttributeIdentifier, OutputMode, DemoProgramGroup, ProgramGroupIdentifier
from model.demo_config import DemoCfg
from parser.config_parser import ConfigParser


class DemoConfigParser:


    @staticmethod
    def _parse_demo_output_mode(params: dict, cfg: DemoCfg) -> None:
        for config_entry in params:
            if config_entry == DemoAttributeIdentifier.OUTPUT_MODE:
                if params[DemoAttributeIdentifier.OUTPUT_MODE] == OutputMode.TMUX:
                    cfg.output_mode = OutputMode.TMUX
                    return
                elif params[DemoAttributeIdentifier.OUTPUT_MODE] == OutputMode.PYTHON:
                    cfg.output_mode = OutputMode.PYTHON
                    return
                else:
                    logging.warning("Unknown output mode in demo config! Use default setting: PYTHON") # TODO: define default somewhere?
                    cfg.output_mode = OutputMode.PYTHON
        logging.warning("Output mode in demo config is undefined! Use default setting: PYTHON")
        cfg.output_mode = OutputMode.PYTHON

    @staticmethod
    def _parse_demo_program_group(params: dict, cfg: DemoCfg) -> None:
        return cfg


    @staticmethod
    def parse_demo_cfg(params: dict, default_working_dir: str) -> DemoCfg:
        logging.info(f"Parsing demo config file")
        demo_cfg = DemoCfg()
        DemoConfigParser._parse_demo_output_mode(params, demo_cfg)
        DemoConfigParser._parse_demo_program_group(params, demo_cfg)

        return demo_cfg

