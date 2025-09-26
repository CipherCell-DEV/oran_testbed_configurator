import logging
import os.path

from model.core_config import CoreImplementation
from model.gnb_config import GNBImplementation
from model.component_repositories import ORAN_SC_RIC_REPO, SRS_RAN_REPO, SRS_RAN_4G_REPO
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

    def _clone_repository(self, repo: str, name: str, folder: str) -> None:
        """
        Clone a Git repository into <build_dir>/<folder> if it does not already exist.
        """
        destination = os.path.join(self._setup_cfg.environment.build_dir, folder)
        if not os.path.exists(os.path.join(self._setup_cfg.environment.build_dir, folder)):
            logging.info(f"Cloning {name} from {repo}")
            try:
                Repo.clone_from(repo, destination)
                logging.info(f"{name} cloned successfully.")
            except Exception as e:
                logging.error(f"Failed to clone {name} from {repo}: {e}")
        else:
            logging.info(f"{folder} already exists at {destination}, skipping clone.")

    def checkout_ric(self):
        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.ORAN_SC_RIC:
            self._clone_repository(repo=ORAN_SC_RIC_REPO, name="ORAN SC RIC", folder='oran-sc-ric')

        if self._setup_cfg.near_rt_ric.implementation == RICImplementation.FLEX_RIC:
            logging.info(f"Flex-RIC currently not supported")

    def checkout_5g_core(self):
        if self._setup_cfg.core_5g.implementation == CoreImplementation.SRS:
            self._clone_repository(repo=SRS_RAN_REPO, name="srsRAN Project", folder='srsRAN_Project')
        else:
            logging.info(f"Other 5G Core implementations currently not supported")

    def checkout_gnb(self):
        if self._setup_cfg.gnb.implementation == GNBImplementation.SRS:
            self._clone_repository(repo=SRS_RAN_REPO, name="srsRAN Project", folder='srsRAN_Project')
        else:
            logging.info(f"Other gnB implementations currently not supported")

    def checkout_ue(self):
        for ue in self._setup_cfg.ue:
            if ue.implementation == UEImplementation.SRS_4G:
                self._clone_repository(repo=SRS_RAN_4G_REPO, name="srsRAN 4G", folder='srsRAN_4G')
            else:
                logging.info(f"Other UE implementations currently not supported")
