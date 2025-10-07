import logging

from model.demo_config import DemoAttributeIdentifier, OutputMode, DemoProgramGroup, ProgramGroupIdentifier, \
    ProgramAttributeIdentifier, ProgramGroupAttributeIdentifier, DemoProgram, DemoCfg


class DemoConfigParser:


    @staticmethod
    def _parse_demo_output_mode(params: dict, cfg: DemoCfg) -> None:
        for config_entry in params:
            if config_entry == DemoAttributeIdentifier.OUTPUT_MODE.value:
                if params[DemoAttributeIdentifier.OUTPUT_MODE.value] == OutputMode.TMUX.value:
                    cfg.output_mode = OutputMode.TMUX
                    return
                elif params[DemoAttributeIdentifier.OUTPUT_MODE.value] == OutputMode.PYTHON.value:
                    cfg.output_mode = OutputMode.PYTHON
                    return
                else:
                    logging.warning(f"Unknown output mode in demo config! Use default setting: {OutputMode.PYTHON.name}") # TODO: define default somewhere?
                    cfg.output_mode = OutputMode.PYTHON
        logging.warning(f"Output mode in demo config is undefined! Use default setting: {OutputMode.PYTHON.name}")
        cfg.output_mode = OutputMode.PYTHON


    @staticmethod
    def _parse_demo_program(params: dict, group: DemoProgramGroup, default_working_dir : str) -> None:
        for config_entry in params:
            demo_p = DemoProgram()
            demo_p.name = config_entry[ProgramAttributeIdentifier.NAME.value]
            demo_p.starting_order = config_entry[ProgramAttributeIdentifier.STARTING_ORDER.value]
            if config_entry.keys().__contains__(ProgramAttributeIdentifier.WORKING_DIRECTORY.value):
                if (config_entry[ProgramAttributeIdentifier.WORKING_DIRECTORY.value] is None) or (config_entry[ProgramAttributeIdentifier.WORKING_DIRECTORY.value] == "") :
                    logging.warning(f"Invalid working directory for program {demo_p.name}. Using build directory {default_working_dir} as default.")
                    demo_p.working_directory= default_working_dir
                else:
                    demo_p.working_directory = config_entry[ProgramAttributeIdentifier.WORKING_DIRECTORY.value]
            else:
                demo_p.working_directory = default_working_dir
            if config_entry[ProgramAttributeIdentifier.COMMAND.value] is not None:
                demo_p.command.extend(config_entry[ProgramAttributeIdentifier.COMMAND.value])
            else:
                logging.error(f"Program {demo_p.name} has no associated command!")
                exit(1)
            if config_entry[ProgramAttributeIdentifier.SUCCESS_INDICATION.value] is not None:
                demo_p.success_indication.extend(config_entry[ProgramAttributeIdentifier.SUCCESS_INDICATION.value])

            group.programs.append(demo_p)


    @staticmethod
    def _parse_demo_program_group(params: dict, cfg: DemoCfg, default_working_dir : str) -> None:
        for config_entry in params:
            if config_entry == DemoAttributeIdentifier.PROGRAM_GROUPS.value:
                for group in params[config_entry]:
                    new_group = DemoProgramGroup()
                    match group:
                        case ProgramGroupIdentifier.CORE.value:
                            new_group.group_type = ProgramGroupIdentifier.CORE
                        case ProgramGroupIdentifier.RIC.value:
                            new_group.group_type = ProgramGroupIdentifier.RIC
                        case ProgramGroupIdentifier.GNB.value:
                            new_group.group_type = ProgramGroupIdentifier.GNB
                        case ProgramGroupIdentifier.UE.value:
                            new_group.group_type = ProgramGroupIdentifier.UE
                        case _:
                            new_group.group_type = ProgramGroupIdentifier.MISC
                    new_group.group_name = group # With this we can still distinguish the MISC groups by name
                    for group_attr in params[config_entry][group]:
                        if group_attr == ProgramGroupAttributeIdentifier.RESTART_TIMEOUT.value:
                            new_group.restart_timeout = params[config_entry][group][group_attr]
                        elif group_attr == ProgramGroupAttributeIdentifier.RESTART_MAX_NUM.value:
                            new_group.restart_max_num = params[config_entry][group][group_attr]
                        elif group_attr == ProgramGroupAttributeIdentifier.PROGRAM_LIST.value:
                            DemoConfigParser._parse_demo_program(params[config_entry][group][group_attr], new_group, default_working_dir)
                    cfg.program_groups.append(new_group)


    @staticmethod
    def parse_demo_cfg(params: dict, default_working_dir: str) -> DemoCfg:
        logging.info(f"Parsing demo config file")
        demo_cfg = DemoCfg()
        DemoConfigParser._parse_demo_output_mode(params, demo_cfg)
        DemoConfigParser._parse_demo_program_group(params, demo_cfg, default_working_dir)
        demo_cfg.check_validity()
        return demo_cfg

