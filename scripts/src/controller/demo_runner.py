from controller.program import Program, ProgramType
from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.ric_config import RICImplementation
from model.setup_configuration import SetupConfiguration
from model.ue_config import UEImplementation


class DemoRunner:
    """
    Orchestrates the setup and execution of demo components (RIC, Core, gNB, UE).
    Builds a pool of `Program` instances that can later be executed.
    """

    def __init__(self, setup_cfg: SetupConfiguration):
        self._cfg = setup_cfg
        self._program_pool: dict[str: Program] = {}

    def get_programs(self) -> dict[str: Program]:
        """
        Get the list of prepared Program instances.

        @return: A list of Program objects.
        """
        return self._program_pool

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

    def _create_ric(self):
        """Create the Near-RT RIC program."""
        if self._cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            self._program_pool.update({'ric': Program(
                working_dir=self._cfg.environment.build_dir,
                name="RIC",
                command=["docker", "compose", "up", "dbaas", "rtmgr_sim", "submgr", "e2term", "appmgr",
                         "e2mgr", "python_xapp_runner"],
                setup_cfg=self._cfg,
                program_type=ProgramType.RIC,
                enable_program_state_checker=True
            )})
        else:
            raise KeyError(
                f"Selected Near-RT RIC implementation '{self._cfg.near_rt_ric.implementation}' is not supported"
            )

    def _create_core(self):
        """Create the 5G Core program."""
        if self._cfg.core_5g.implementation == CoreImplementation.SRS:
            self._program_pool.update({'5g_core': Program(working_dir=self._cfg.environment.build_dir,
                                                          name="5G-core",
                                                          command=["docker", "compose", "up", "5gc"],
                                                          setup_cfg=self._cfg,
                                                          program_type=ProgramType.CORE,
                                                          enable_program_state_checker=True)})
        else:
            raise KeyError(
                f"Selected 5G Core implementation '{self._cfg.core_5g.implementation}' is not supported"
            )

    def _create_gnb(self):
        """Create the gNB program."""
        if self._cfg.gnb.implementation == GNBImplementation.SRS:
            self._program_pool.update({'gnb': Program(
                working_dir=self._cfg.environment.build_dir,
                name="gNB",
                command=["docker", "compose", "up", "gnb"],
                setup_cfg=self._cfg,
                program_type=ProgramType.GNB,
                enable_program_state_checker=True)}
            )
        else:
            raise KeyError(
                f"Selected gNB implementation '{self._cfg.gnb.implementation}' is not supported"
            )

    def _create_ues(self):
        """Create programs for all configured UEs."""
        for ue in self._cfg.ue:
            if ue.implementation == UEImplementation.SRS_4G:
                if 'ue' not in self._program_pool:
                    self._program_pool.update({'ue': []})
                self._program_pool['ue'].append(Program(
                    working_dir=self._cfg.environment.build_dir,
                    name=f"UE-{ue.name}",
                    # Do not remove --force-recreate, otherwise the PDU Session Establishment will not be successful.
                    command=["docker", "compose", "up", "--force-recreate", ue.name],
                    setup_cfg=self._cfg,
                    program_type=ProgramType.UE,
                    enable_program_state_checker=True
                ))
            else:
                raise KeyError(
                    f"Selected UE implementation '{ue.implementation}' is not supported"
                )

    @property
    def cfg(self):
        return self._cfg
