import logging

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.ric_config import RICImplementation
from model.setup_configuration import GeneralIdentifiers, ComponentIdentifiers
from model.ue_config import UEImplementation
from model.utils_config import BuildType


class ParsingUtils:
    @staticmethod
    def parse_build_type(params: dict, component_name: ComponentIdentifiers):
        if GeneralIdentifiers.BUILD_TYPE in params:
            if params[GeneralIdentifiers.BUILD_TYPE] == 'docker':
                return BuildType.DOCKER
            elif params[GeneralIdentifiers.BUILD_TYPE] == 'native':
                return BuildType.NATIVE
            else:
                raise ValueError(f"Unsupported build type: {params[GeneralIdentifiers.BUILD_TYPE]}")
        else:
            raise KeyError(
                f"Missing required parameter for {component_name} config: '{params[GeneralIdentifiers.BUILD_TYPE]}'")

    @staticmethod
    def parse_implementation(params: dict, component_name: ComponentIdentifiers):
        if GeneralIdentifiers.IMPLEMENTATION in params:
            match component_name:
                case ComponentIdentifiers.CFG_NEAR_RT_RIC:
                    match params[GeneralIdentifiers.IMPLEMENTATION]:
                        case RICImplementation.ORAN_SC_RIC.value:
                            return RICImplementation.ORAN_SC_RIC
                        case RICImplementation.FLEX_RIC.value:
                            return RICImplementation.FLEX_RIC
                        case _:
                            raise ValueError(f"Unsupported RIC implementation: {params[GeneralIdentifiers.IMPLEMENTATION]}")
                case ComponentIdentifiers.CFG_GNB:
                    match params[GeneralIdentifiers.IMPLEMENTATION]:
                        case GNBImplementation.SRS.value:
                            return GNBImplementation.SRS
                        case _:
                            raise ValueError(f"Unsupported GNB implementation: {params[GeneralIdentifiers.IMPLEMENTATION]}")
                case ComponentIdentifiers.CFG_5GC:
                    match params[GeneralIdentifiers.IMPLEMENTATION]:
                        case CoreImplementation.OPEN5GS_SRS.value:
                            return CoreImplementation.OPEN5GS_SRS
                        case CoreImplementation.OPEN5GS.value:
                            return CoreImplementation.OPEN5GS
                        case _:
                            raise ValueError(f"Unsupported Core implementation: {params[GeneralIdentifiers.IMPLEMENTATION]}")
                case ComponentIdentifiers.CFG_UE:
                    match params[GeneralIdentifiers.IMPLEMENTATION]:
                        case UEImplementation.SRS_4G.value:
                            return UEImplementation.SRS_4G
                        case _:
                            raise ValueError(f"Unsupported UE implementation: {params[GeneralIdentifiers.IMPLEMENTATION]}")
        else:
            raise KeyError(
                f"Missing required parameter for {component_name} config: '{GeneralIdentifiers.IMPLEMENTATION}'")

    @staticmethod
    def parse_commit(params: dict, component_name: ComponentIdentifiers):
        if GeneralIdentifiers.COMMIT in params:
            commit = params[GeneralIdentifiers.COMMIT]
            logging.info(f"Identified Commit {commit} for {component_name}")
            return commit
        else:
            logging.info(f"{GeneralIdentifiers.COMMIT} not specified -> use latest for {component_name}")
            return "latest"

    @staticmethod
    def parse_repository(params: dict, component_name: ComponentIdentifiers):
        if GeneralIdentifiers.REPOSITORY in params:
            repository = params[GeneralIdentifiers.REPOSITORY]
            logging.info(f"Identified Repository {repository} for {component_name}")
            return repository
        else:
            raise KeyError(f"Missing required parameter for {component_name} config: '{GeneralIdentifiers.REPOSITORY}'")