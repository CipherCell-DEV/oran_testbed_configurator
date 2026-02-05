import ipaddress
from unittest.mock import patch

import pytest

from controller.parser.gnb_config_parser import GNBConfigParser
from model.gnb_config import GnbFieldIdentifiers, DefaultValuesGNB, GNBIPConfig
from model.setup_configuration import GeneralIdentifiers


class TestGNBConfigParser:
    """Unit tests for GNBConfigParser"""

    def test_parse_gnb_network_success(self):
        params = {
            "e2": "10.0.0.1",
            "ru_sdr": "10.0.0.2",
            "cu_cp": "10.0.0.3",
        }

        cfg = GNBConfigParser._parse_gnb_network(params)

        assert isinstance(cfg, GNBIPConfig)
        assert cfg.e2 == ipaddress.IPv4Address("10.0.0.1")
        assert cfg.ru_sdr == ipaddress.IPv4Address("10.0.0.2")
        assert cfg.cu_cp == ipaddress.IPv4Address("10.0.0.3")

    def test_parse_gnb_network_missing_key(self):
        params = {
            "e2": "10.0.0.1",
            "ru_sdr": "10.0.0.2",
            # cu_cp missing
        }

        with pytest.raises(KeyError, match="Missing required parameter for gNB IP config: 'cu_cp'"):
            GNBConfigParser._parse_gnb_network(params)

    def test_convert_srate(self):
        result = GNBConfigParser._convert_srate(5000000)
        assert result == 5.0

    @patch("controller.parser.gnb_config_parser.ParsingUtils")
    def test_parse_gnb_cfgs_full(self, mock_utils):
        params = {
            GnbFieldIdentifiers.NETWORK: {
                "e2": "10.0.0.1",
                "ru_sdr": "10.0.0.2",
                "cu_cp": "10.0.0.3",
            },
            GeneralIdentifiers.VENDOR: [
                {
                    "implementation": "srs",
                    "build_type": "docker",
                    "repository": "https://docker.ciphercell.de",
                    "commit": "abcdef",
                    GnbFieldIdentifiers.SRATE: 5000000,
                    GnbFieldIdentifiers.TX_GAIN: 10,
                    GnbFieldIdentifiers.RX_GAIN: 20,
                }
            ]
        }

        mock_utils.parse_build_type.return_value = "docker"
        mock_utils.parse_implementation.return_value = "srs"
        mock_utils.parse_commit.return_value = "abcdef"
        mock_utils.parse_repository.return_value = "https://docker.ciphercell.de"

        gnbs = GNBConfigParser.parse_gnb_cfgs(params)

        assert len(gnbs) == 1
        gnb = gnbs[0]

        assert gnb.implementation == "srs"
        assert gnb.build_type == "docker"
        assert gnb.commit == "abcdef"
        assert gnb.repository == "https://docker.ciphercell.de"
        assert gnb.srate == 5.0
        assert gnb.tx_gain == 10
        assert gnb.rx_gain == 20
        assert gnb.ip_config.e2 == ipaddress.IPv4Address("10.0.0.1")

    @patch("controller.parser.gnb_config_parser.ParsingUtils")
    def test_parse_gnb_cfgs_missing_optional_fields(self, mock_utils, caplog):
        params = {
            GnbFieldIdentifiers.NETWORK: {
                "e2": "10.0.0.1",
                "ru_sdr": "10.0.0.2",
                "cu_cp": "10.0.0.3",
            },
            GeneralIdentifiers.VENDOR: [
                {
                    "implementation": "srs",
                    "build_type": "docker",
                    "repository": "https://docker.ciphercell.de",
                    "commit": "abcdef",
                    # srate, tx_gain, rx_gain missing
                }
            ]
        }

        mock_utils.parse_build_type.return_value = "docker"
        mock_utils.parse_implementation.return_value = "srs"
        mock_utils.parse_commit.return_value = "abcdef"
        mock_utils.parse_repository.return_value = "https://docker.ciphercell.de",

        with caplog.at_level("WARNING"):
            gnbs = GNBConfigParser.parse_gnb_cfgs(params)

        gnb = gnbs[0]

        assert gnb.srate == DefaultValuesGNB.DEFAULT_SRATE
        assert gnb.tx_gain == DefaultValuesGNB.TX_GAIN
        assert gnb.rx_gain == DefaultValuesGNB.RX_GAIN
        assert "No srate specified" in caplog.text
        assert "No tx_gain specified" in caplog.text
        assert "No rx_gain specified" in caplog.text

    @patch("controller.parser.gnb_config_parser.ParsingUtils")
    def test_parse_gnb_cfgs_no_vendors(self, mock_utils, caplog):
        params = {
            GnbFieldIdentifiers.NETWORK: {
                "e2": "10.0.0.1",
                "ru_sdr": "10.0.0.2",
                "cu_cp": "10.0.0.3",
            },
            # No vendors
        }

        with caplog.at_level("WARNING"):
            gnbs = GNBConfigParser.parse_gnb_cfgs(params)

        assert gnbs == []
        assert "No gNBs found" in caplog.text
