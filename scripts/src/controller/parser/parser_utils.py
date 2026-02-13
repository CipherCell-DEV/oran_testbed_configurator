"""
Utility functions for parsing common configuration parameters from
YAML or dictionary inputs for various components like Core, gNB, RIC,
and UE. Provides standardized methods to extract build type, implementation,
commit, and repository information for setup configuration objects.
"""

import logging

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.ric_config import RICImplementation
from model.setup_configuration import GeneralIdentifiers, ComponentIdentifiers
from model.ue_config import UEImplementation
from model.utils_config import BuildType


class ParsingUtils:
    """Helper methods to parse component configuration parameters."""

    @staticmethod
    def parse_build_type(params: dict, component_name: ComponentIdentifiers):
        """
        Parse the build type from the component configuration (e.g. Docker, Native)s.
        Returns a ValueError in case of unsupported build type.
        """
        if GeneralIdentifiers.BUILD_TYPE in params:
            if params[GeneralIdentifiers.BUILD_TYPE] == "docker":
                return BuildType.DOCKER
            if params[GeneralIdentifiers.BUILD_TYPE] == "native":
                return BuildType.NATIVE
            raise ValueError(
                f"Unsupported build type: {params[GeneralIdentifiers.BUILD_TYPE]}"
            )
        raise KeyError(
            f"Missing required parameter for {component_name} config: "
            f"'{GeneralIdentifiers.BUILD_TYPE}'"
        )

    @staticmethod
    def parse_implementation(params: dict, component_name: ComponentIdentifiers):
        """
        Parse the implementation type for a given component from configuration parameters.
        Returns the corresponding Enum member for the component's implementation.
        """

        if GeneralIdentifiers.IMPLEMENTATION in params:
            match component_name:
                case ComponentIdentifiers.CFG_NEAR_RT_RIC:
                    return ParsingUtils._parse_ric_implementation(params)

                case ComponentIdentifiers.CFG_GNB:
                    return ParsingUtils._parse_gnb_implementation(params)

                case ComponentIdentifiers.CFG_5GC:
                    return ParsingUtils._parse_core_implementation(params)

                case ComponentIdentifiers.CFG_UE:
                    return ParsingUtils._parse_ue_implementation(params)
        else:
            raise KeyError(
                f"Missing required parameter for {component_name} config: '"
                f"{GeneralIdentifiers.IMPLEMENTATION}'"
            )

    @staticmethod
    def parse_commit(params: dict, component_name: ComponentIdentifiers):
        """
        Parse the commit (revision number) from the component configuration.
        If non is specified return latest.
        """
        if GeneralIdentifiers.COMMIT in params:
            commit = params[GeneralIdentifiers.COMMIT]
            logging.info("Identified Commit %s for %s", commit, component_name)
            return commit
        logging.info(
            "%s not specified -> use latest for %s",
            GeneralIdentifiers.COMMIT,
            component_name,
        )
        return "latest"

    @staticmethod
    def parse_repository(params: dict, component_name: ComponentIdentifiers):
        """Parse the repository URL from the component configuration."""

        if GeneralIdentifiers.REPOSITORY in params:
            repository = params[GeneralIdentifiers.REPOSITORY]
            logging.info("Identified Repository %s for %s", repository, component_name)
            return repository
        raise KeyError(
            f"Missing required parameter for {component_name} config: "
            f"'{GeneralIdentifiers.REPOSITORY}'"
        )

    @staticmethod
    def _parse_ric_implementation(params: dict) -> RICImplementation:
        """
        Helper method to return the RIC implementation from the component configuration.
        """
        match params[GeneralIdentifiers.IMPLEMENTATION]:
            case RICImplementation.ORAN_SC_RIC.value:
                return RICImplementation.ORAN_SC_RIC
            case RICImplementation.FLEX_RIC.value:
                return RICImplementation.FLEX_RIC
            case _:
                raise ValueError(
                    f"Unsupported RIC implementation: "
                    f"{params[GeneralIdentifiers.IMPLEMENTATION]}"
                )

    @staticmethod
    def _parse_gnb_implementation(params: dict) -> GNBImplementation:
        """
        Helper method to return the RIC implementation from the component configuration.
        """
        match params[GeneralIdentifiers.IMPLEMENTATION]:
            case GNBImplementation.SRS.value:
                return GNBImplementation.SRS
            case _:
                raise ValueError(
                    f"Unsupported GNB implementation: "
                    f"{params[GeneralIdentifiers.IMPLEMENTATION]}"
                )

    @staticmethod
    def _parse_core_implementation(params: dict) -> CoreImplementation:
        """
        Helper method to return the 5G Core implementation from the component configuration.
        """
        match params[GeneralIdentifiers.IMPLEMENTATION]:
            case CoreImplementation.OPEN5GS_SRS.value:
                return CoreImplementation.OPEN5GS_SRS
            case CoreImplementation.OPEN5GS.value:
                return CoreImplementation.OPEN5GS
            case _:
                raise ValueError(
                    f"Unsupported Core implementation: "
                    f"{params[GeneralIdentifiers.IMPLEMENTATION]}"
                )

    @staticmethod
    def _parse_ue_implementation(params: dict) -> UEImplementation:
        """
        Helper method to return the UE implementation from the component configuration.
        """
        match params[GeneralIdentifiers.IMPLEMENTATION]:
            case UEImplementation.SRS_4G.value:
                return UEImplementation.SRS_4G
            case _:
                raise ValueError(
                    f"Unsupported UE implementation: "
                    f"{params[GeneralIdentifiers.IMPLEMENTATION]}"
                )
