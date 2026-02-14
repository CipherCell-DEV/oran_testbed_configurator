from unittest.mock import patch

import pytest

from controller.parser.parser_utils import ParsingUtils
from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.ric_config import RICImplementation
from model.setup_configuration import ComponentIdentifiers, GeneralIdentifiers
from model.ue_config import UEImplementation
from model.utils_config import BuildType


class TestParsingUtils:

    def test_parse_build_type_valid(self):
        params = {GeneralIdentifiers.BUILD_TYPE: 'docker'}
        assert ParsingUtils.parse_build_type(params, ComponentIdentifiers.CFG_5GC) == BuildType.DOCKER

        params = {GeneralIdentifiers.BUILD_TYPE: 'native'}
        assert ParsingUtils.parse_build_type(params, ComponentIdentifiers.CFG_GNB) == BuildType.NATIVE

    def test_parse_build_type_invalid(self):
        params = {GeneralIdentifiers.BUILD_TYPE: 'unsupported'}
        with pytest.raises(ValueError):
            ParsingUtils.parse_build_type(params, ComponentIdentifiers.CFG_UE)

    def test_parse_build_type_missing(self):
        params = {}
        with pytest.raises(KeyError):
            ParsingUtils.parse_build_type(params, ComponentIdentifiers.CFG_5GC)

    def test_parse_implementation_valid(self):
        params = {GeneralIdentifiers.IMPLEMENTATION: 'oran_sc_ric'}
        assert (ParsingUtils.parse_implementation(params, ComponentIdentifiers.CFG_NEAR_RT_RIC) ==
                RICImplementation.ORAN_SC_RIC)

        params = {GeneralIdentifiers.IMPLEMENTATION: 'srs'}
        assert ParsingUtils.parse_implementation(params, ComponentIdentifiers.CFG_GNB) == GNBImplementation.SRS

        params = {GeneralIdentifiers.IMPLEMENTATION: 'open5gs'}
        assert ParsingUtils.parse_implementation(params, ComponentIdentifiers.CFG_5GC) == CoreImplementation.OPEN5GS

        params = {GeneralIdentifiers.IMPLEMENTATION: 'srs_4g'}
        assert ParsingUtils.parse_implementation(params, ComponentIdentifiers.CFG_UE) == UEImplementation.SRS_4G

    def test_parse_implementation_invalid(self):
        params = {GeneralIdentifiers.IMPLEMENTATION: 'unknown_impl'}
        with pytest.raises(ValueError):
            ParsingUtils.parse_implementation(params, ComponentIdentifiers.CFG_5GC)

    def test_parse_implementation_missing(self):
        params = {}
        with pytest.raises(KeyError):
            ParsingUtils.parse_implementation(params, ComponentIdentifiers.CFG_UE)

    @patch("logging.info")
    def test_parse_commit_with_value(self, mock_log):
        params = {GeneralIdentifiers.COMMIT: "abcdef123"}
        assert ParsingUtils.parse_commit(params, ComponentIdentifiers.CFG_5GC) == "abcdef123"
        mock_log.assert_called_once()

    @patch("logging.info")
    def test_parse_commit_missing(self, mock_log):
        params = {}
        assert ParsingUtils.parse_commit(params, ComponentIdentifiers.CFG_5GC) == "latest"
        mock_log.assert_called_once()

    @patch("logging.info")
    def test_parse_repository_valid(self, mock_log):
        params = {GeneralIdentifiers.REPOSITORY: "https://ciphercell.git"}
        repo = ParsingUtils.parse_repository(params, ComponentIdentifiers.CFG_GNB)
        assert repo == "https://ciphercell.git"
        mock_log.assert_called_once()

    def test_parse_repository_missing(self):
        params = {}
        with pytest.raises(KeyError):
            ParsingUtils.parse_repository(params, ComponentIdentifiers.CFG_UE)
