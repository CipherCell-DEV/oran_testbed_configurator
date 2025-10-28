import logging
from typing import List, Optional

from pkg_resources import non_empty_lines

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
        """Create the Near-RT RIC program."""
        if self._cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            rics = self._cfg.programs.get_ric_programs()
            # TODO: allow partial deployment (e.g. no RICs)? Might come in handy in future hardware integration tests ...
            if len(rics) == 0:
                logging.warning("No RIC will be started.")
            if len(rics) > 1:
                logging.warning(f"Only one RIC is currently supported. Will only start program {rics[0].name}.")
            self._program_pool.append(rics[0])
        else:
            raise KeyError(
                f"Selected Near-RT RIC implementation '{self._cfg.near_rt_ric.implementation}' is not supported"
            )

    def _create_core(self):
        """Create the 5G Core program."""
        if self._cfg.core_5g.implementation == CoreImplementation.OPEN5GS_SRS:
            cores = self._cfg.programs.get_core_programs()
            if len(cores) == 0:
                logging.warning("No core will be started.")
            if len(cores) > 1:
                logging.warning(f"Only one core is currently supported. Will only start program {cores[0].name}")
            self._program_pool.append(cores[0])
        else:
            raise KeyError(
                f"Selected 5G Core implementation '{self._cfg.core_5g.implementation}' is not supported"
            )

    def _create_gnb(self):
        """Create the gNB program."""
        if self._cfg.gnb.implementation == GNBImplementation.SRS:
            gnbs = self._cfg.programs.get_gnb_programs()
            if len(gnbs) == 0:
                logging.warning("No gnb will be started.")
            if len(gnbs) > 1:
                logging.warning(f"Only one gnb is currently supported. Will only start program {gnbs[0].name}")
            self._program_pool.append(gnbs[0])
        else:
            raise KeyError(
                f"Selected gNB implementation '{self._cfg.gnb.implementation}' is not supported"
            )

    def _create_ues(self):
        """Create programs for all configured UEs."""
        for ue in self._cfg.ue:
            if ue.implementation == UEImplementation.SRS_4G:
                ue_programs = self._cfg.programs.get_ue_programs()
                if len(ue_programs) == 0:
                    logging.warning("No UEs will be started.")
                if len(ue_programs) > 1:
                    logging.warning(f"About to start multiple UEs!")
                for program in ue_programs:
                    self._program_pool.append(program)
            else:
                raise KeyError(
                    f"Selected UE implementation '{ue.implementation}' is not supported"
                )


    def _create_misc(self):
        """All other programs are added without further restrictions"""
        for program in self._cfg.programs.get_misc_programs():
            self._program_pool.append(program)

