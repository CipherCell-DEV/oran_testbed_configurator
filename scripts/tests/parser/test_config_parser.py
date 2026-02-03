import pytest
from unittest.mock import patch, MagicMock

from controller.parser.config_parser import ConfigParser
from model.setup_configuration import ComponentIdentifiers
from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.ric_config import RICImplementation


class TestConfigParser:
    """Unit tests for ConfigParser"""

    # -------------------------
    # Environment config tests
    # -------------------------

    def test_parse_environment_cfg_valid(self):
        params = {
            "core_implementation": "open5gs",
            "gnb_implementation": "srs",
            "ric_implementation": "oran_sc_ric",
            "log_level": "DEBUG",
            "log_dir": "logs",
            "build_dir": "build",
            "docker_registry": "docker.ciphercell.com",
            "tag_appendix": "dev",
            "push_local_images": True,
        }

        cfg = ConfigParser._parse_environment_cfg(params)

        assert cfg.core_implementation == CoreImplementation.OPEN5GS
        assert cfg.gnb_implementation == GNBImplementation.SRS
        assert cfg.ric_implementation == RICImplementation.ORAN_SC_RIC
        assert cfg.log_level == "DEBUG"
        assert cfg.docker_registry == "docker.ciphercell.com"
        assert cfg.tag_appendix == "dev"
        assert cfg.push_local_images is True

    def test_parse_environment_cfg_default_log_level(self, caplog):
        params = {
            "build_dir": "build"
        }

        with caplog.at_level("WARNING"):
            cfg = ConfigParser._parse_environment_cfg(params)

        assert cfg.log_level == "INFO"
        assert "No log level specified" in caplog.text

    def test_parse_environment_cfg_invalid_log_level(self):
        params = {
            "build_dir": "build",
            "log_level": "TRACE",
        }

        with pytest.raises(ValueError, match="Unsupported log level"):
            ConfigParser._parse_environment_cfg(params)

    def test_parse_environment_cfg_missing_build_dir(self):
        params = {}

        with pytest.raises(KeyError, match="Missing required parameter"):
            ConfigParser._parse_environment_cfg(params)