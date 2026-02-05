import ipaddress
from unittest.mock import patch

import pytest

from controller.parser.near_rt_ric_config_parser import NearRTRICConfigParser
from model.ric_config import (
    RICFieldIdentifiers,
    DefaultValuesRIC,
    NearRTRICNetworkConfig,
)
from model.setup_configuration import GeneralIdentifiers


class TestNearRTRICConfigParser:
    """Unit tests for NearRTRICConfigParser."""

    def test_parse_network_config_success(self):
        params = {
            "subnet": "10.0.0.0/24",
            "dbaas_ip": "10.0.0.10",
            "e2term_ip": "10.0.0.11",
            "e2mgr_ip": "10.0.0.12",
            "submgr_ip": "10.0.0.13",
            "appmgr_ip": "10.0.0.14",
            "rtmgr_sim_ip": "10.0.0.15",
            "xapp_runner_ip": "10.0.0.16",
        }

        cfg = NearRTRICConfigParser._parse_network_config(params)
        assert isinstance(cfg, NearRTRICNetworkConfig)
        assert cfg.subnet == ipaddress.IPv4Network("10.0.0.0/24")
        assert cfg.dbaas_ip == ipaddress.IPv4Address("10.0.0.10")
        assert cfg.e2mgr_ip == ipaddress.IPv4Address("10.0.0.12")

    def test_parse_network_config_missing_key(self):
        params = {
            "subnet": "10.0.0.0/24",
            "dbaas_ip": "10.0.0.10",
            # missing e2term_ip
        }

        with pytest.raises(KeyError, match="Missing required parameter for near-RT RIC IP config: 'e2term_ip'"):
            NearRTRICConfigParser._parse_network_config(params)

    def test_parse_network_config_ip_out_of_subnet(self):
        params = {
            "subnet": "10.0.0.0/24",
            "dbaas_ip": "10.0.1.10",  # outside subnet
            "e2term_ip": "10.0.0.11",
            "e2mgr_ip": "10.0.0.12",
            "submgr_ip": "10.0.0.13",
            "appmgr_ip": "10.0.0.14",
            "rtmgr_sim_ip": "10.0.0.15",
            "xapp_runner_ip": "10.0.0.16",
        }

        with pytest.raises(ValueError, match="is not in the configured subnet"):
            NearRTRICConfigParser._parse_network_config(params)

    @patch("controller.parser.near_rt_ric_config_parser.ParsingUtils")
    def test_parse_near_rt_ric_cfgs_full(self, mock_utils):
        params = {
            RICFieldIdentifiers.NETWORK: {
                "subnet": "10.0.0.0/24",
                "dbaas_ip": "10.0.0.10",
                "e2term_ip": "10.0.0.11",
                "e2mgr_ip": "10.0.0.12",
                "submgr_ip": "10.0.0.13",
                "appmgr_ip": "10.0.0.14",
                "rtmgr_sim_ip": "10.0.0.15",
                "xapp_runner_ip": "10.0.0.16",
            },
            GeneralIdentifiers.VENDOR: [
                {
                    "implementation": "oran_sc_ric",
                    "build_type": "docker",
                    "repository": "https://docker.ciphercell.de",
                    "commit": "abcdef",
                    "release": "m"
                }
            ]
        }

        mock_utils.parse_build_type.return_value = "docker"
        mock_utils.parse_implementation.return_value = "oran_sc_ric"
        mock_utils.parse_commit.return_value = "abcdef"
        mock_utils.parse_repository.return_value = "https://docker.ciphercell.de"

        rics = NearRTRICConfigParser.parse_near_rt_ric_cfgs(params)
        assert len(rics) == 1
        ric = rics[0]
        assert ric.build_type == "docker"
        assert ric.implementation == "oran_sc_ric"
        assert ric.commit == "abcdef"
        assert ric.repository == "https://docker.ciphercell.de"
        assert ric.ip_config.subnet == ipaddress.IPv4Network("10.0.0.0/24")

    @patch("controller.parser.near_rt_ric_config_parser.ParsingUtils")
    def test_parse_near_rt_ric_cfgs_missing_network(self, mock_utils, caplog):
        params = {
            # no network key
            GeneralIdentifiers.VENDOR: [
                {"implementation": "oran_sc_ric"}
            ]
        }

        with caplog.at_level("WARNING"):
            rics = NearRTRICConfigParser.parse_near_rt_ric_cfgs(params)

        assert len(rics) == 1
        ric = rics[0]
        assert ric.ip_config.subnet == DefaultValuesRIC.DEFAULT_NETWORK_CONFIG['subnet']
        assert "No IP address specified" in caplog.text

    @patch("controller.parser.near_rt_ric_config_parser.ParsingUtils")
    def test_parse_near_rt_ric_cfgs_no_vendors(self, mock_utils, caplog):
        params = {
            RICFieldIdentifiers.NETWORK: {
                "subnet": "10.0.0.0/24",
                "dbaas_ip": "10.0.0.10",
                "e2term_ip": "10.0.0.11",
                "e2mgr_ip": "10.0.0.12",
                "submgr_ip": "10.0.0.13",
                "appmgr_ip": "10.0.0.14",
                "rtmgr_sim_ip": "10.0.0.15",
                "xapp_runner_ip": "10.0.0.16",
            }
        }

        with caplog.at_level("WARNING"):
            rics = NearRTRICConfigParser.parse_near_rt_ric_cfgs(params)

        assert rics == []
        assert "No RICs are defined" in caplog.text
