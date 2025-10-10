import logging

from program_descr_config import ProgramDescriptionCfg, TerminalIdentifiers, TerminalDescription, OutputIdentifiers, \
    OutputMode, ProgramDescription, ProgramIdentifiers, ProgramDescrGroup, ProgramGroupIdentifier


class ProgramConfigParser:

    @staticmethod
    def _parse_terminal_data(params: dict, cfg : ProgramDescriptionCfg):
        if TerminalIdentifiers.TERMINALS.value in params:
            for terminal in params[TerminalIdentifiers.TERMINALS.value]:
                t_data = TerminalDescription()
                t_data.name = terminal
                if TerminalIdentifiers.SUBPROC_PREFIX.value in params[TerminalIdentifiers.TERMINALS.value][terminal]:
                    t_data.subproc_prefix.extend([TerminalIdentifiers.TERMINALS.value][terminal][TerminalIdentifiers.SUBPROC_PREFIX.value])
                if TerminalIdentifiers.SUBPROC_POSTFIX.value in params[TerminalIdentifiers.TERMINALS.value][terminal]:
                    t_data.subprocess_postfix.extend([TerminalIdentifiers.TERMINALS.value][terminal][TerminalIdentifiers.SUBPROC_POSTFIX.value])
                cfg.terminal_descriptions.append(t_data)


    @staticmethod
    def _parse_output_data(params: dict, cfg: ProgramDescriptionCfg) -> None:
        if OutputIdentifiers.OUTPUT_MODE.value in params:
            if params[OutputIdentifiers.OUTPUT_MODE.value] == OutputMode.PYTHON.value:
                cfg.output_mode = OutputMode.PYTHON
            if params[OutputIdentifiers.OUTPUT_MODE.value] == OutputMode.TMUX.value:
                cfg.output_mode = OutputMode.TMUX
        if OutputIdentifiers.OUTPUT_SETTINGS.value in params:
            if OutputIdentifiers.LOG_DIR.value in params[OutputIdentifiers.OUTPUT_SETTINGS.value]:
                cfg.log_dir = params[OutputIdentifiers.OUTPUT_SETTINGS.value][OutputIdentifiers.LOG_DIR.value]
            if cfg.log_dir is not None or cfg.log_dir == "":
                logging.warning(f"{cfg.config_file_path}: No dedicated log_dir folder given!")
        if cfg.output_mode == OutputMode.PYTHON:
            if params[OutputIdentifiers.SHOW_NUM_LINES.value] in params[OutputIdentifiers.OUTPUT_SETTINGS.value]:
                cfg.show_num_lines = params[OutputIdentifiers.OUTPUT_SETTINGS.value][OutputIdentifiers.SHOW_NUM_LINES.value]
        if cfg.output_mode == OutputMode.TMUX:
            if params[OutputIdentifiers.SESSION_PREFIX.value] in params[OutputIdentifiers.OUTPUT_SETTINGS.value]:
                cfg.session_prefix = params[OutputIdentifiers.OUTPUT_SETTINGS.value][OutputIdentifiers.SESSION_PREFIX.value]
            if params[OutputIdentifiers.PANES_PER_SESSION.value] in params[OutputIdentifiers.OUTPUT_SETTINGS.value]:
                cfg.panes_per_session = params[OutputIdentifiers.OUTPUT_SETTINGS.value][OutputIdentifiers.PANES_PER_SESSION.value]


    @staticmethod
    def _parse_program_descr(params: dict, group: ProgramDescrGroup, default_working_dir : str) -> None:
        for config_entry in params:
            p_desc = ProgramDescription()
            if ProgramIdentifiers.PROGRAM_NAME.value in config_entry:
                p_desc.name = config_entry[ProgramIdentifiers.PROGRAM_NAME.value]
            if ProgramIdentifiers.PROGRAM_DEPENDS.value in config_entry:
                p_desc.depends_on_names.extend(config_entry[ProgramIdentifiers.PROGRAM_DEPENDS.value])
            if ProgramIdentifiers.PROGRAM_COMMAND.value in config_entry:
                p_desc.command.extend(config_entry[ProgramIdentifiers.PROGRAM_COMMAND.value])
            if ProgramIdentifiers.PROGRAM_WORKING_DIRECTORY.value in config_entry:
                p_desc.working_dir = params[ProgramIdentifiers.PROGRAM_WORKING_DIRECTORY.value]
                if p_desc.working_dir == "":
                    logging.warning(f"{p_desc.name}: Invalid working directory {p_desc.working_dir}. Will use environment build directory instead.")
                    p_desc.working_dir = default_working_dir
            else:
                p_desc.working_dir = default_working_dir
            if ProgramIdentifiers.PROGRAM_STATE_TRANSITIONS.value in config_entry:
                if ProgramIdentifiers.PROGRAM_TRANSITION_STOP_INIT.value in config_entry[ProgramIdentifiers.PROGRAM_STATE_TRANSITIONS.value]:
                    p_desc.transition_init_run = config_entry[ProgramIdentifiers.PROGRAM_STATE_TRANSITIONS.value][
                        ProgramIdentifiers.PROGRAM_TRANSITION_STOP_INIT.value]
                if ProgramIdentifiers.PROGRAM_TRANSITION_INIT_RUN.value in config_entry[ProgramIdentifiers.PROGRAM_STATE_TRANSITIONS.value]:
                    p_desc.transition_init_run = config_entry[ProgramIdentifiers.PROGRAM_STATE_TRANSITIONS.value][
                        ProgramIdentifiers.PROGRAM_TRANSITION_INIT_RUN.value]
            group.programs.append(p_desc)


    @staticmethod
    def _parse_program_descr_groups(params: dict, cfg: ProgramDescriptionCfg, default_working_dir : str) -> None:
        if ProgramIdentifiers.PROGRAM_GROUPS.value in params:
            for group in params[ProgramIdentifiers.PROGRAM_GROUPS.value]:
                new_group = ProgramDescrGroup()
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
                new_group.groups = group # With this we can still distinguish the MISC groups by name
                if ProgramIdentifiers.RESTART_TIMEOUT.value in params[group]:
                    new_group.timeout = params[group][ProgramIdentifiers.RESTART_TIMEOUT.value]
                if ProgramIdentifiers.RESTART_MAX_NUM.value in params[group]:
                    new_group.max_num = params[group][ProgramIdentifiers.RESTART_MAX_NUM.value]
                if ProgramIdentifiers.PROGRAM_LIST in params[group]:
                    ProgramConfigParser._parse_program_descr(params[group][ProgramIdentifiers.PROGRAM_LIST.value],
                                                             new_group, default_working_dir)
                cfg.program_groups.append(new_group)


    @staticmethod
    def parse_program_cfg(file_path: str, params: dict, default_working_dir: str) -> ProgramDescriptionCfg:
        logging.info(f"Parsing program config file")
        program_cfg = ProgramDescriptionCfg()
        program_cfg.config_file_path = file_path
        ProgramConfigParser._parse_terminal_data(params, program_cfg)
        ProgramConfigParser._parse_output_data(params, program_cfg)
        ProgramConfigParser._parse_program_descr_groups(params, program_cfg, default_working_dir)
        return program_cfg

