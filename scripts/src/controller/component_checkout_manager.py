import logging
import os.path

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.component_repositories import ORAN_SC_RIC_REPO, SRS_RAN_REPO, SRS_RAN_4G_REPO, OPEN5GS_REPO
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
        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            self._clone_repository(repo=ORAN_SC_RIC_REPO, name="ORAN SC RIC", folder='oran-sc-ric',
                                   commit=self._setup_cfg.near_rt_ric.commit)

        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.FLEX_RIC:
            logging.error(f"Flex-RIC currently not supported")
            exit(1)

    def checkout_5g_core(self):
        if self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS_SRS:
            self._clone_repository(repo=SRS_RAN_REPO, name="srsRAN Project", folder='srsRAN_Project',
                                   commit=self._setup_cfg.core_5g.commit)
        elif self._setup_cfg.core_5g.implementation == CoreImplementation.OPEN5GS:
            self._clone_repository(repo=OPEN5GS_REPO, name="open5gs", folder='open5gs',
                                   commit=self._setup_cfg.core_5g.commit)
        else:
            logging.error(f"Other 5G Core implementations currently not supported")
            exit(1)

    def checkout_gnb(self):
        if self._setup_cfg.gnb.implementation == GNBImplementation.SRS:
            self._clone_repository(repo=SRS_RAN_REPO, name="srsRAN Project", folder='srsRAN_Project',
                                   commit=self._setup_cfg.gnb.commit)
        else:
            logging.error(f"Other gnB implementations currently not supported")
            exit(1)

    def checkout_ue(self):
        for ue in self._setup_cfg.ue.ues:
            if ue.implementation == UEImplementation.SRS_4G:
                self._clone_repository(repo=SRS_RAN_4G_REPO, name="srsRAN 4G", folder='srsRAN_4G',
                                       commit=ue.commit)
            else:
                logging.error(f"Other UE implementations currently not supported")
                exit(1)
