import logging

from model.setup_configuration import GeneralIdentifiers
from model.utils_config import BuildType


class ParsingUtils:
    @staticmethod
    def parse_build_type(params: dict, component_name: str):
        if GeneralIdentifiers.BUILD_TYPE in params:
            if params[GeneralIdentifiers.BUILD_TYPE] == 'docker':
                return BuildType.DOCKER
            elif params[GeneralIdentifiers.BUILD_TYPE] == 'local':
                return BuildType.NATIVE
            else:
                raise ValueError(f"Unsupported build type: {params[GeneralIdentifiers.BUILD_TYPE]}")
        else:
            raise KeyError(
                f"Missing required parameter for {component_name} config: '{params[GeneralIdentifiers.BUILD_TYPE]}'")

    @staticmethod
    def parse_implementation(params: dict, allowed_values: dict, component_name: str):
        if GeneralIdentifiers.IMPLEMENTATION in params:
            if any(params[GeneralIdentifiers.IMPLEMENTATION] == idn for idn in allowed_values.keys()):
                return allowed_values[params[GeneralIdentifiers.IMPLEMENTATION]]
            else:
                raise ValueError(f"Unsupported {component_name} type: {params[GeneralIdentifiers.IMPLEMENTATION]}")
        else:
            raise KeyError(
                "Missing required parameter for {component_name} config: '{CoreFieldIdentifiers.IMPLEMENTATION}'")

    @staticmethod
    def parse_commit(params: dict, component_name: str):
        if GeneralIdentifiers.COMMIT in params:
            commit = params[GeneralIdentifiers.COMMIT]
            logging.info(f"Identified Commit {commit} for {component_name}")
            return commit
        else:
            logging.info(f"{GeneralIdentifiers.COMMIT} not specified -> use latest for {component_name}")
            return "latest"
