import logging

from model.program_descr_config import ProgramDescriptionCfg, TerminalIdentifiers, TerminalDescription, OutputIdentifiers, \
    OutputMode, ProgramDescription, ProgramIdentifiers, ProgramDescrGroup, ProgramGroupIdentifier


class ProgramConfigParser:

    @staticmethod
    def _parse_terminal_data(params: dict, cfg : ProgramDescriptionCfg):
        if TerminalIdentifiers.TERMINALS.value in params:
            for terminal_dict in params[TerminalIdentifiers.TERMINALS.value]:
                for terminal  in terminal_dict:
                    t_data = TerminalDescription()
                    t_data.name = terminal
                    if TerminalIdentifiers.SUBPROC_PREFIX.value in terminal_dict[terminal]:
                        t_data.subproc_prefix = terminal_dict[terminal][TerminalIdentifiers.SUBPROC_PREFIX.value]
                    if TerminalIdentifiers.SUBPROC_POSTFIX.value in terminal_dict[terminal]:
                        t_data.subprocess_postfix = terminal_dict[terminal][TerminalIdentifiers.SUBPROC_POSTFIX.value]
                    if cfg.terminal_descriptions is None:
                        cfg.terminal_descriptions = [t_data]
                    else:
                        cfg.terminal_descriptions.append(t_data)
        if TerminalIdentifiers.USED_TERMINAL.value in params:
            cfg.used_terminal = params[TerminalIdentifiers.USED_TERMINAL.value]

    @staticmethod
    def _parse_output_data(params: dict, cfg: ProgramDescriptionCfg) -> None:
        if OutputIdentifiers.OUTPUT_MODE.value in params:
            if params[OutputIdentifiers.OUTPUT_MODE.value] == OutputMode.PYTHON.value:
                cfg.output_mode = OutputMode.PYTHON
            if params[OutputIdentifiers.OUTPUT_MODE.value] == OutputMode.TMUX.value:
                cfg.output_mode = OutputMode.TMUX
        if OutputIdentifiers.OUTPUT_SETTINGS.value in params:
            output_settings = params[OutputIdentifiers.OUTPUT_SETTINGS.value]
            if OutputIdentifiers.LOG_DIR.value in output_settings:
                cfg.log_dir = output_settings[OutputIdentifiers.LOG_DIR.value]
            if cfg.log_dir is None or cfg.log_dir == "":
                logging.warning(f"{cfg.config_file_path}: No dedicated log_dir folder given!")
            if cfg.output_mode == OutputMode.PYTHON:
                output_settings_python = output_settings[OutputMode.PYTHON.value]
                if OutputIdentifiers.SHOW_NUM_LINES.value in output_settings_python:
                    cfg.show_num_lines = output_settings_python[OutputIdentifiers.SHOW_NUM_LINES.value]
            if cfg.output_mode == OutputMode.TMUX:
                output_settings_tmux = output_settings[OutputMode.TMUX.value]
                if OutputIdentifiers.SESSION_PREFIX.value in output_settings_tmux:
                    cfg.session_prefix = output_settings_tmux[OutputIdentifiers.SESSION_PREFIX.value]
                if OutputIdentifiers.PANES_PER_SESSION.value in output_settings_tmux:
                    cfg.panes_per_session = output_settings_tmux[OutputIdentifiers.PANES_PER_SESSION.value]


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
                p_desc.working_directory = config_entry[ProgramIdentifiers.PROGRAM_WORKING_DIRECTORY.value]
                if p_desc.working_directory == "":
                    logging.warning(f"{p_desc.name}: Invalid working directory {p_desc.working_directory}. Will use environment build directory instead.")
                    p_desc.working_directory = default_working_dir
            else:
                p_desc.working_directory = default_working_dir
            if ProgramIdentifiers.PROGRAM_STATE_TRANSITIONS.value in config_entry:
                state_transitions = config_entry[ProgramIdentifiers.PROGRAM_STATE_TRANSITIONS.value]
                if ProgramIdentifiers.PROGRAM_TRANSITION_STOP_INIT.value in state_transitions:
                    p_desc.transition_stop_to_init = state_transitions[ProgramIdentifiers.PROGRAM_TRANSITION_STOP_INIT.value]
                if ProgramIdentifiers.PROGRAM_TRANSITION_INIT_RUN.value in state_transitions:
                    p_desc.transition_init_run = state_transitions[ProgramIdentifiers.PROGRAM_TRANSITION_INIT_RUN.value]
            p_desc.update_group_data(group.restart_timeout, group.restart_max_num)
            group.programs.append(p_desc)


    @staticmethod
    def _parse_program_descr_groups(params: dict, cfg: ProgramDescriptionCfg, default_working_dir : str) -> None:
        if ProgramIdentifiers.PROGRAM_GROUPS.value in params:
            group_section = params[ProgramIdentifiers.PROGRAM_GROUPS.value]
            for group in group_section:
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
                new_group.group_name = group # With this we can still distinguish the MISC groups by name
                if ProgramIdentifiers.RESTART_TIMEOUT.value in group_section[group]:
                    new_group.restart_timeout = group_section[group][ProgramIdentifiers.RESTART_TIMEOUT.value]
                if ProgramIdentifiers.RESTART_MAX_NUM.value in group_section[group]:
                    new_group.restart_max_num = group_section[group][ProgramIdentifiers.RESTART_MAX_NUM.value]
                if ProgramIdentifiers.PROGRAM_LIST.value in group_section[group]:
                    ProgramConfigParser._parse_program_descr(group_section[group][ProgramIdentifiers.PROGRAM_LIST.value],
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

