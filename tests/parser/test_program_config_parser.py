import pytest

from controller.parser.program_config_parser import ProgramConfigParser
from model.program_descr_config import (
    ProgramDescriptionCfg,
    TerminalIdentifiers,
    OutputIdentifiers,
    OutputMode,
    ProgramIdentifiers,
    ProgramGroupIdentifier,
)


class TestProgramConfigParser:

    @pytest.fixture
    def empty_cfg(self):
        return ProgramDescriptionCfg()

    def test_parse_terminal_data_with_default_terminal(self, empty_cfg):
        params = {
            TerminalIdentifiers.TERMINALS.value: [
                {
                    "xterm": {
                        TerminalIdentifiers.SUBPROC_PREFIX.value: "pre",
                        TerminalIdentifiers.SUBPROC_POSTFIX.value: "post",
                    }
                }
            ],
            TerminalIdentifiers.DEFAULT_TERMINAL.value: "xterm",
        }

        ProgramConfigParser._parse_terminal_data(params, empty_cfg)

        assert empty_cfg.terminal_descriptions is not None
        assert len(empty_cfg.terminal_descriptions) == 1
        term = empty_cfg.terminal_descriptions[0]

        assert term.name == "xterm"
        assert term.subproc_prefix == "pre"
        assert term.subprocess_postfix == "post"
        assert empty_cfg.get_used_terminal() == term

    def test_parse_terminal_data_invalid_default_terminal(self, empty_cfg, caplog):
        params = {
            TerminalIdentifiers.TERMINALS.value: [{"xterm": {}}],
            TerminalIdentifiers.DEFAULT_TERMINAL.value: "invalid",
        }

        ProgramConfigParser._parse_terminal_data(params, empty_cfg)

        assert empty_cfg.get_used_terminal() is None
        assert "not found in terminal list" in caplog.text

    def test_parse_output_data_python_mode(self, empty_cfg):
        params = {
            OutputIdentifiers.OUTPUT_MODE.value: OutputMode.PYTHON.value,
            OutputIdentifiers.OUTPUT_SETTINGS.value: {
                OutputIdentifiers.LOG_DIR.value: "/tmp/logs",
                OutputMode.PYTHON.value: {
                    OutputIdentifiers.SHOW_NUM_LINES.value: 10
                },
            },
        }

        ProgramConfigParser._parse_output_data(params, empty_cfg)

        assert empty_cfg.output_mode == OutputMode.PYTHON
        assert empty_cfg.log_dir == "/tmp/logs"
        assert empty_cfg.show_num_lines == 10

    def test_parse_output_data_tmux_mode(self, empty_cfg):
        params = {
            OutputIdentifiers.OUTPUT_MODE.value: OutputMode.TMUX.value,
            OutputIdentifiers.OUTPUT_SETTINGS.value: {
                OutputIdentifiers.LOG_DIR.value: "/tmp/logs",
                OutputMode.TMUX.value: {
                    OutputIdentifiers.SESSION_PREFIX.value: "sess",
                    OutputIdentifiers.PANES_PER_SESSION.value: 4,
                },
            },
        }

        ProgramConfigParser._parse_output_data(params, empty_cfg)

        assert empty_cfg.output_mode == OutputMode.TMUX
        assert empty_cfg.session_prefix == "sess"
        assert empty_cfg.panes_per_session == 4

    def test_parse_program_groups_and_programs(self, empty_cfg):
        params = {
            ProgramIdentifiers.PROGRAM_GROUPS.value: {
                ProgramGroupIdentifier.CORE.value: {
                    ProgramIdentifiers.RESTART_TIMEOUT.value: 5,
                    ProgramIdentifiers.RESTART_MAX_NUM.value: 3,
                    ProgramIdentifiers.PROGRAM_LIST.value: [
                        {
                            ProgramIdentifiers.PROGRAM_NAME.value: "core_app",
                            ProgramIdentifiers.PROGRAM_COMMAND.value: ["run"],
                        }
                    ],
                }
            }
        }

        ProgramConfigParser._parse_program_descr_groups(
            params, empty_cfg, default_working_dir="/work"
        )

        assert len(empty_cfg.program_groups) == 1
        group = empty_cfg.program_groups[0]

        assert group.group_type == ProgramGroupIdentifier.CORE
        assert group.restart_timeout == 5
        assert group.restart_max_num == 3
        assert len(group.programs) == 1

        program = group.programs[0]
        assert program.name == "core_app"
        assert program.command == ["run"]
        assert program.working_directory == "/work"

    def test_parse_program_cfg_end_to_end(self):
        params = {
            TerminalIdentifiers.TERMINALS.value: [{"bash": {}}],
            TerminalIdentifiers.DEFAULT_TERMINAL.value: "bash",
            ProgramIdentifiers.PROGRAM_GROUPS.value: {},
        }

        cfg = ProgramConfigParser.parse_program_cfg(
            file_path="config.yml",
            params=params,
            default_working_dir="/default",
        )

        assert cfg.config_file_path == "config.yml"
        assert cfg.get_used_terminal().name == "bash"
        assert cfg.program_groups == []
