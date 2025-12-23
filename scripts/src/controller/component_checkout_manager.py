import logging
import os.path

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.ric_config import RICImplementation
from model.setup_configuration import SetupConfiguration

from git import Repo

from model.ue_config import UEImplementation


class ComponentCheckoutManager:
    """
    Fetches/clones the required software components (RIC, Core, gNB, UE)
    according to a SetupConfiguration.
    """

    def __init__(self, setup_config: SetupConfiguration):
        self._setup_cfg = setup_config

    def _clone_repository(self, repo: str, name: str, folder: str, commit: str) -> None:
        """
        Clone a Git repository into <build_dir>/<folder> if it does not already exist.
        """
        destination = os.path.join(self._setup_cfg.environment.build_dir, folder)
        if not os.path.exists(os.path.join(self._setup_cfg.environment.build_dir, folder)):
            logging.info(f"Cloning {name} from {repo}")
            try:
                git_repository = Repo.clone_from(repo, destination)
                if not commit == 'latest':
                    logging.info(f"Checkout specific commit {commit}")
                    git_repository.git.checkout(commit)
                logging.info(f"{name} cloned successfully.")
            except Exception as e:
                logging.error(f"Failed to clone {name} from {repo}: {e}")
        else:
            logging.info(f"{folder} already exists at {destination}, skipping clone.")

    def checkout_ric(self):
        ric = self._setup_cfg.get_used_ric()
        if ric is not None:
            if ric.implementation == RICImplementation.ORAN_SC_RIC:
                self._clone_repository(repo=ric.repository, name="ORAN SC RIC",
                                       folder='oran-sc-ric', commit=ric.commit)
            elif ric.implementation == RICImplementation.FLEX_RIC:
                self._clone_repository(repo=ric.repository, name="flexric",
                                       folder='flexric', commit=ric.commit)
            else:
                logging.error(f"Unknown RIC implementation {ric.implementation}")
                exit(1)
        else:
            logging.warning(f"No RIC implementation specified for checkout")

    def checkout_5g_core(self):
        core = self._setup_cfg.get_used_core()
        if core is not None:
            if core.implementation == CoreImplementation.OPEN5GS_SRS:
                self._clone_repository(repo=core.repository, name="srsRAN Project",
                                       folder='srsRAN_Project', commit=core.commit)
            elif core.implementation == CoreImplementation.OPEN5GS:
                self._clone_repository(repo=core.repository, name="open5gs",
                                       folder='open5gs', commit=core.commit)
            else:
                logging.error(f"Unknown Core implementation {core.implementation}")
                exit(1)
        else:
            logging.warning(f"No Core implementation specified for checkout")


    def checkout_gnb(self):
        gnb = self._setup_cfg.get_used_gnb()
        if gnb is not None:
            if gnb.implementation == GNBImplementation.SRS:
                self._clone_repository(repo=gnb.repository, name="srsRAN Project",
                                       folder='srsRAN_Project', commit=gnb.commit)
            else:
                logging.error(f"Unknown gNB implementation {gnb.implementation}")
                exit(1)
        else:
            logging.warning(f"No gNB implementation specified for checkout")


    def checkout_ue(self):
        for ue in self._setup_cfg.ue.ues:
            if ue.implementation == UEImplementation.SRS_4G:
                self._clone_repository(repo=ue.repository, name="srsRAN 4G", folder='srsRAN_4G',
                                       commit=ue.commit)
            else:
                logging.error(f"Other UE implementations currently not supported")
                exit(1)
