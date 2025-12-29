import os
from enum import Enum

from fastapi import HTTPException, FastAPI, status
from pydantic import BaseModel
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from api.api_state import APIStatus, RepositoryCheckoutStatus, ComponentState
from controller.builder.build_runner import BuildRunner
from model.setup_configuration import SetupConfiguration, EnvironmentCfg
from main_utils import checkout_repositories as checkout_repos_util, patch_firmware

setup_configuration = SetupConfiguration()


class StatusResponse(BaseModel):
    status: str


class BuildSelector(Enum):
    RIC = "near-rt-ric"
    CORE_5G = "core5g"
    GNB = "gnb"
    UE = "ue"
    ZMQ_PROXY = "zmq-proxy"
    ALL = "all"


def setup_default_setup_configuration() -> SetupConfiguration:
    setup_configuration.environment = EnvironmentCfg()
    setup_configuration.environment.log_dir = os.path.join(os.getcwd(), "logs")
    setup_configuration.environment.log_level = "INFO"
    setup_configuration.environment.build_dir = os.path.join(os.getcwd(), "repositories")
    setup_configuration.environment.push_local_images = "false"
    return setup_configuration


def mount_folders(app):
    """
    Mounter folder containing figures required by the landing page.
    """
    app.mount("/doc", StaticFiles(directory="./doc"), name="doc")
    return Jinja2Templates(directory="scripts/src/api/templates")


def setup_fast_api():
    app = FastAPI()
    return app, mount_folders(app)


def check_configuration(setup_cfg: SetupConfiguration) -> HTTPException | None:
    if not setup_cfg.near_rt_rics:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=f"Near RT RIC configuration is missing. Run near-rt-ric-config first.")
    elif not setup_cfg.cores_5g:
        return HTTPException(status_code=400, detail=f"Core 5G configuration is missing. Run core5g-config first.")
    elif not setup_cfg.gnbs:
        return HTTPException(status_code=400, detail=f"gNB configuration is missing. Run gnb-config first.")
    elif not setup_cfg.ue:
        return HTTPException(status_code=400,
                             detail=f"UE configuration is missing. Run ue-config-list and ue-config first.")
    return None


def run_checkout(setup_cfg: SetupConfiguration, api_status: APIStatus):
    """
    Function that actually performs the checkout.
    Runs in a separate thread.
    """
    try:
        ret = check_configuration(setup_cfg)
        if ret:
            # You could log this error since HTTPException won't propagate in background
            print(f"Configuration error: {ret.detail}")
            return
        checkout_repos_util(setup_cfg)
        api_status.repositories_checked_out = RepositoryCheckoutStatus.CHECKED_OUT
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to checkout repositories: {e}")


def run_build(component: BuildSelector, setup_cfg: SetupConfiguration, api_status: APIStatus) -> bool:
    patch_firmware(setup_cfg)
    build_runner = BuildRunner(setup_configuration=setup_configuration)

    if component == BuildSelector.RIC or component == BuildSelector.ALL:
        if not build_runner.build_ric():
            api_status.set_component_status(BuildSelector.RIC, ComponentState.BUILD_FAILED)
            return False
        if component == BuildSelector.CORE_5G or component == BuildSelector.ALL:
            if not build_runner.build_5g_core():
                api_status.set_component_status(BuildSelector.CORE_5G, ComponentState.BUILD_FAILED)
                return False
        if component == BuildSelector.GNB or component == BuildSelector.ALL:
            if not build_runner.build_gnb():
                api_status.set_component_status(BuildSelector.GNB, ComponentState.BUILD_FAILED)

                return False
        if component == BuildSelector.UE or component == BuildSelector.ALL:
            if not build_runner.build_ues():
                return False
    return True


def format_time_difference(total_seconds: int) -> str:
    """
    Turns a timedelta object into a representation of HH-MM-SS.
    """
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}-{minutes}-{seconds}"
