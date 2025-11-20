import logging
from typing import List, Optional

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.ric_config import RICImplementation
from model.setup_configuration import SetupConfiguration
from model.ue_config import UEImplementation
from model.program_descr_config import ProgramDescription


class DemoRunner:
    """
    Orchestrates the setup and execution of demo components (RIC, Core, gNB, UE, misc.).
    Builds a pool of `Program` instances that can later be executed.
    """

    def __init__(self, setup_cfg: SetupConfiguration):
        self._cfg = setup_cfg
        self._program_pool: List[ProgramDescription] = []

    @property
    def programs(self):
        """
        Get the list of prepared Program instances.

        @return: A list of Program objects.
        """
        return self._program_pool


    @property
    def cfg(self):
        return self._cfg


    def create_programs(self):
        """
        Create Program objects for each configured component based on setup_cfg.

        Adds each created Program into the internal program pool.
        Raises KeyError if the selected implementation is not supported.
        """
        self._create_ric()
        self._create_core()
        self._create_gnb()
        self._create_ues()
        self._create_misc()

    def _create_ric(self):
        """
        Create the Near-RT RIC program.
        Chooses a Near-RT RIC program which matches the implementation type from the build stage.
        The demo configuration may have several RIC programs defined. Only one of them is chosen.
        """
        ric_added = False
        for ric_impl in self._cfg.programs.get_ric_programs():
            if ric_impl.ric_implementation is not None and ric_impl.ric_implementation == self._cfg.near_rt_ric.implementation:
                if ric_added is False:
                    self._program_pool.append(ric_impl)
                    ric_added = True
                else:
                    logging.warning(f"Found multiple RIC programs matching {ric_impl.ric_implementation.value}!")
        if not ric_added:
            logging.warning(f"No RIC for implementation {self._cfg.near_rt_ric.implementation.value} found! No RIC will be started.")

    def _create_core(self):
        """
        Create the 5G Core program.
        Chooses a 5G Core program which matches the implementation type from the build stage.
        The demo configuration may have several Core programs defined. Only one of them is chosen.
        """
        core_added = False
        for core_impl in self._cfg.programs.get_core_programs():
            if core_impl.core_implementation is not None and core_impl.core_implementation == self._cfg.core_5g.implementation:
                if core_added is False:
                    self._program_pool.append(core_impl)
                    core_added = True
                else:
                    logging.warning(f"Found multiple Core programs matching {core_impl.core_implementation.value}!")
        if not core_added:
            logging.warning(
                f"No Core for implementation {self._cfg.core_5g.implementation.value} found! No Core will be started.")

    def _create_gnb(self):
        """
        Create the gNB program.
        Chooses a gNB program which matches the implementation type from the build stage.
        The demo configuration may have several gNB programs defined. Only one of them is chosen.
        """
        gnb_added = False
        for gnb_impl in self._cfg.programs.get_gnb_programs():
            if gnb_impl.gnb_implementation is not None and gnb_impl.gnb_implementation == self._cfg.gnb.implementation:
                if gnb_added is False:
                    self._program_pool.append(gnb_impl)
                    gnb_added = True
                else:
                    logging.warning(f"Found multiple gNB programs matching {gnb_impl.gnb_implementation.value}!")
        if not gnb_added:
            logging.warning(
                f"No gNB for implementation {self._cfg.gnb.implementation.value} found! No gNB will be started.")

    def _create_ues(self):
        """
        Create programs for all configured UEs.
        Chooses UEs which match the implementation type from the build stage.
        """
        for ue_impl in self._cfg.programs.get_ue_programs():
            ue_added = False
            if ue_impl.ue_implementation is not None:
                # find ue with same name in both demo con and build conf and make sure they are the same ue implementation
                for ue_build_data in self._cfg.ue.ues:
                    if (ue_impl.name == ue_build_data.name) and (ue_impl.ue_implementation == ue_build_data.implementation):
                        logging.info(f"Found matching ue configuration for {ue_impl.name}")
                        self._program_pool.append(ue_impl)
                        ue_added = True
                        break
            if not ue_added:
                logging.warning(f"Found no matching build configuration for {ue_impl.name}. Please check sample config.")

    def _create_misc(self):
        """All other programs are added without further restrictions"""
        for program in self._cfg.programs.get_misc_programs():
            self._program_pool.append(program)

