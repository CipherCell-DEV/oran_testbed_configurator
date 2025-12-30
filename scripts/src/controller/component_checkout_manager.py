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
        self._last_error = ""

    def get_last_error(self):
        return self._last_error

    def _clone_repository(self, repo: str, name: str, folder: str, commit: str) -> bool:
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
                error_str = f"Failed to clone {name} from {repo}: {e}"
                logging.error(error_str)
                self._last_error = error_str
                return False
        else:
            logging.info(f"{folder} already exists at {destination}, skipping clone.")
        return True

    def checkout_ric(self) -> bool:
        ric = self._setup_cfg.get_used_ric()
        if ric is not None:
            if ric.implementation == RICImplementation.ORAN_SC_RIC:
                if not self._clone_repository(repo=ric.repository, name="ORAN SC RIC",
                                              folder='oran-sc-ric', commit=ric.commit):
                    return False
            elif ric.implementation == RICImplementation.FLEX_RIC:
                if not self._clone_repository(repo=ric.repository, name="flexric",
                                              folder='flexric', commit=ric.commit):
                    return False
            else:
                error_str = f"Unknown RIC implementation {ric.implementation}"
                logging.error(error_str)
                self._last_error = error_str
                return False
        else:
            err_msg = "No RIC implementation specified for checkout"
            logging.warning(err_msg)
            self._last_error = "No RIC implementation specified for checkout"
        return True

    def checkout_5g_core(self) -> bool:
        core = self._setup_cfg.get_used_core()
        if core is not None:
            if core.implementation == CoreImplementation.OPEN5GS_SRS:
                if not self._clone_repository(repo=core.repository, name="srsRAN Project",
                                              folder='srsRAN_Project', commit=core.commit):
                    return False
            elif core.implementation == CoreImplementation.OPEN5GS:
                if not self._clone_repository(repo=core.repository, name="open5gs",
                                              folder='open5gs', commit=core.commit):
                    return False
            else:
                err_msg = f"Unknown Core implementation {core.implementation}"
                logging.error(err_msg)
                self._last_error = err_msg
                return False
        else:
            err_msg = "No Core implementation specified for checkout"
            logging.warning(err_msg)
            self._last_error = err_msg
        return True

    def checkout_gnb(self) -> bool:
        gnb = self._setup_cfg.get_used_gnb()
        if gnb is not None:
            if gnb.implementation == GNBImplementation.SRS:
                if not self._clone_repository(repo=gnb.repository, name="srsRAN Project",
                                              folder='srsRAN_Project', commit=gnb.commit):
                    return False
            else:
                err_msg = f"Unknown gNB implementation {gnb.implementation}"
                logging.error(err_msg)
                self._last_error = err_msg
                return False
        else:
            err_msg = "No gNB implementation specified for checkout"
            logging.warning(err_msg)
            self._last_error = err_msg
        return True

    def checkout_ue(self) -> bool:
        for ue in self._setup_cfg.ue.ues:
            if ue.implementation == UEImplementation.SRS_4G:
                if not self._clone_repository(repo=ue.repository, name="srsRAN 4G", folder='srsRAN_4G',
                                              commit=ue.commit):
                    return False
            else:
                err_msg = "Other UE implementations currently not supported"
                logging.error(err_msg)
                self._last_error = err_msg
                return False
        return True
