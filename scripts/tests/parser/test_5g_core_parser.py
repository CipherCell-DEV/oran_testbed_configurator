import ipaddress
from unittest.mock import patch

import pytest

from controller.parser.core_5g_config_parser import Core5GConfigParser
from model.core_config import CoreFieldIdentifiers
from model.setup_configuration import GeneralIdentifiers


class TestCore5GConfigParser:
    """Unit tests for Core5GConfigParser"""

    @pytest.fixture
    def valid_network_cfg(self):
        return {
            CoreFieldIdentifiers.NETWORK: {
                CoreFieldIdentifiers.CORE_IP: "10.0.0.1",
                CoreFieldIdentifiers.SUBNET: "10.0.0.0/24",
                CoreFieldIdentifiers.MONGO_DB_IP: "10.0.0.2",
            }
        }

    @pytest.fixture
    def valid_5gc_cfg(self, valid_network_cfg):
        return {
            **valid_network_cfg,
            GeneralIdentifiers.VENDOR: [
                {
                    "implementation": "open5gs",
                    "build_type": "docker",
                    "repository": "https://repo.ciphercell.com",
                    "commit": "abcdef",
                }
            ]
        }

    @patch("controller.parser.core_5g_config_parser.ParsingUtils")
    def test_parse_5g_cfgs_success(self, mock_utils, valid_5gc_cfg):
        mock_utils.parse_build_type.return_value = "docker"
        mock_utils.parse_implementation.return_value = "open5gs"
        mock_utils.parse_commit.return_value = "abcdef"
        mock_utils.parse_repository.return_value = "https://repo.ciphercell.com"

        cores = Core5GConfigParser.parse_5g_cfgs(valid_5gc_cfg)

        assert len(cores) == 1
        core = cores[0]

        assert core.implementation == "open5gs"
        assert core.build_type == "docker"
        assert core.commit == "abcdef"
        assert core.repository == "https://repo.ciphercell.com"

        assert core.network.ip == ipaddress.IPv4Address("10.0.0.1")
        assert core.network.subnet == ipaddress.IPv4Network("10.0.0.0/24")
        assert core.network.mongodb_ip == ipaddress.IPv4Address("10.0.0.2")

    def test_parse_5g_cfgs_missing_network(self):
        params = {
            GeneralIdentifiers.VENDOR: []
        }

        with pytest.raises(KeyError, match="Missing required parameter for 5GC config"):
            Core5GConfigParser.parse_5g_cfgs(params)

    def test_parse_5g_network_config_missing_field(self):
        params = {
            CoreFieldIdentifiers.NETWORK: {
                CoreFieldIdentifiers.CORE_IP: "10.0.0.1",
                # SUBNET missing
                CoreFieldIdentifiers.MONGO_DB_IP: "10.0.0.2",
            }
        }

        with pytest.raises(KeyError, match="No subnet specified for 5G core"):
            Core5GConfigParser._parse_5g_network_config(params)

    def test_parse_5g_cfgs_no_vendors(self, valid_network_cfg, caplog):
        with caplog.at_level("WARNING"):
            cores = Core5GConfigParser.parse_5g_cfgs(valid_network_cfg)

        assert cores == []
        assert "No 5G Cores are defined" in caplog.text

    def test_parse_5g_network_config_ip_casting(self, valid_network_cfg):
        network = Core5GConfigParser._parse_5g_network_config(valid_network_cfg)

        assert isinstance(network.ip, ipaddress.IPv4Address)
        assert isinstance(network.subnet, ipaddress.IPv4Network)
        assert isinstance(network.mongodb_ip, ipaddress.IPv4Address)
