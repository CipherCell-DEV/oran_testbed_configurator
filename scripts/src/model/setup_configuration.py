import logging
import os
from dataclasses import dataclass, field
from pprint import pformat
from typing import Optional, List

from model.core_config import CoreImplementation
from model.dialog_cfg import DialogConfig
from model.core_config import Core5GCfg
from model.gnb_config import GNBCfg, GNBImplementation
from model.ric_config import NearRtRICCFG, RICRelease, RICImplementation
from model.ue_config import UECfg
from model.utils_config import LogLevel
from model.program_descr_config import ProgramDescriptionCfg
from model.program_descr_config import ProgramGroupIdentifier


class ComponentIdentifiers:
    CFG_NEAR_RT_RIC = "near_rt_ric"
    CFG_5GC = "5gc"
    CFG_UE = "ue"
    CFG_GNB = "gnb"
    CFG_ENVIRONMENT = "environment"


class GeneralIdentifiers:
    BUILD_TYPE = 'build_type'
    IMPLEMENTATION = 'implementation'
    COMMIT = 'commit'
    REPOSITORY = 'repository'
    VENDOR = 'vendors'


class EnvironmentCfg:
    core_implementation: Optional[CoreImplementation] = None
    gnb_implementation: Optional[GNBImplementation] = None
    ric_implementation: Optional[RICImplementation] = None
    log_level: Optional[LogLevel] = None
    log_dir: Optional[str] = None
    build_dir: Optional[str] = None
    docker_registry: Optional[str] = "localhost:4000"
    tag_appendix: Optional[str] = None
    push_local_images: Optional[bool] = False

    def __str__(self):
        return (f"EnvironmentCfg: \n"
                f"    core_implementation: {self.core_implementation}\n"
                f"    gnb_implementation: {self.gnb_implementation}\n"
                f"    ric_implementation: {self.ric_implementation}\n"
                f"    log_level={self.log_level}, \n"
                f"    log_dir={self.log_dir}, \n"
                f"    build_dir={self.build_dir}, \n"
                f"    docker_registry={self.docker_registry}, \n"
                f"    tag_appendix={self.tag_appendix}")


@dataclass
class SetupConfiguration:
    dialog: Optional[DialogConfig] = None
    environment: Optional[EnvironmentCfg] = None
    near_rt_rics: List[NearRtRICCFG] = field(default_factory=list)
    cores_5g: List[Core5GCfg] = field(default_factory=list)
    gnbs: List[GNBCfg] = field(default_factory=list)
    programs: Optional[ProgramDescriptionCfg] = None
    ue: UECfg = field(default_factory=lambda: None)


    def __str__(self):
        return (f"SetupConfiguration: \n"
                f"{self.dialog}\n"
                f"{self.environment}, \n"
                f"{os.sep.join(map(str, self.near_rt_rics))}\n"
                f"{os.sep.join(map(str, self.cores_5g))}, \n"
                f"{os.sep.join(map(str, self.gnbs))}, \n"
                f"{self.programs}, \n"
                f"UECfgs: \n"
                f"{pformat(self.ue, indent=4)}")


    def _combine_cfg_data(self):
        """
        Some configuration data depends on one another.
        """
        # extend relative logging path of the demo configuration
        self.programs.log_dir = os.path.join(self.environment.log_dir, self.programs.log_dir)

    def get_used_core(self) -> Core5GCfg | None:
        """
        From all the available vendor implementations returns the selected core implementation
        """
        if self.environment.core_implementation is not None:
            for impl in self.cores_5g:
                if impl.implementation == self.environment.core_implementation:
                    return impl
        return None

    def get_used_gnb(self) -> GNBCfg | None:
        """
        From all the available vendor implementations returns the selected gnb implementation
        """
        if self.environment.gnb_implementation is not None:
            for impl in self.gnbs:
                if impl.implementation == self.environment.gnb_implementation:
                    return impl
        return None

    def get_used_ric(self) -> NearRtRICCFG | None:
        """
        From all the available vendor implementations returns the selected RIC implementation
        """
        if self.environment.ric_implementation is not None:
            for impl in self.near_rt_rics:
                if impl.implementation == self.environment.ric_implementation:
                    return impl
        return None

    def verify_consistency(self) -> bool:
        """
        This project both manages building the ORAN component and running demo programs.
        We need to make sure that the configuration is consistent across build related data
        and the following program data.
        Things to be checked:
        # TODO: extend this
        - The UE names must be consistent between the sample_configuration.yml and demo_configuration.yml files
        - If we build Open 5gc (not from the srs Project), then we need to run docker compose up 5gc mongodb.
            Print a warning if the demo program does not mention mongodb in this case.
        """
        self._combine_cfg_data()
        if self.programs is not None:
            for group in self.programs.program_groups:
                if group.group_type == ProgramGroupIdentifier.UE:
                    for program in group.programs:
                        valid = False
                        for ue_instance in self.ue.ues:
                            if ue_instance.name == program.name:
                                valid = True
                        if not valid:
                            logging.error(f"{program.name} is not a valid UE name. Please check both build and program configurations")
                            return False
        return True
