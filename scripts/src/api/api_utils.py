import asyncio
import datetime
import logging
import os
from typing import Optional

from fastapi import HTTPException, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from api.api_state import APIStatus, ComponentState
from controller.builder.build_runner import BuildRunner
from controller.component_checkout_manager import ComponentCheckoutManager
from main_utils import patch_firmware
from model.setup_configuration import SetupConfiguration, EnvironmentCfg, ComponentIdentifiers
from model.utils_config import LogLevel

setup_configuration = SetupConfiguration()

current_directory = os.path.dirname(os.path.realpath(__file__))


class APIConfig:
    """Container for FastAPI app, templates, configuration, and runtime status."""

    def __init__(self):
        """Initializes application components and middleware."""
        self._app, self._templates = setup_fast_api()
        self._setup_configuration = setup_default_setup_configuration()
        self._api_status = APIStatus()
        self._up_time = datetime.datetime.now()

        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def get_app(self) -> FastAPI:
        return self._app

    def get_templates(self) -> Jinja2Templates:
        return self._templates

    def get_setup_config(self) -> SetupConfiguration:
        return self._setup_configuration

    def get_api_status(self) -> APIStatus:
        return self._api_status

    def get_up_time(self) -> datetime.datetime:
        return self._up_time


class StatusResponse(BaseModel):
    """Generic API response model containing a status string."""
    status: str


def setup_default_setup_configuration() -> SetupConfiguration:
    """Initializes environment defaults for the setup configuration."""

    setup_configuration.environment = EnvironmentCfg()
    setup_configuration.environment.log_dir = os.path.join(os.getcwd(), "logs")
    setup_configuration.environment.log_level = LogLevel.INFO
    setup_configuration.environment.build_dir = os.path.join(os.getcwd(), "repositories")
    setup_configuration.environment.push_local_images = False
    return setup_configuration


def mount_folders(app):
    """Mounter folder containing figures required by the landing page."""

    app.mount("/doc", StaticFiles(directory=f"{current_directory}/../../../doc"), name="doc")
    return Jinja2Templates(directory=f"{current_directory}/../../../scripts/src/api/templates")


def setup_fast_api():
    """Creates the FastAPI instance and attaches static mounts."""

    app = FastAPI()
    return app, mount_folders(app)


def check_configuration(setup_cfg: SetupConfiguration) -> HTTPException | None:
    """Validates mandatory configuration sections before execution."""

    if not setup_cfg.near_rt_rics:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Near RT RIC configuration is missing. Run near-rt-ric-config first.")
    elif not setup_cfg.cores_5g:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="Core 5G configuration is missing. Run core5g-config first.")
    elif not setup_cfg.gnbs:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="gNB configuration is missing. Run gnb-config first.")
    elif not setup_cfg.ue:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="UE configuration is missing. Run ue-config-list and ue-config first.")
    return None


async def run_checkout(setup_cfg: SetupConfiguration, api_status: APIStatus, loop):
    """
    Function that actually performs the checkout.
    Runs in a separate thread.
    """
    try:
        ret = check_configuration(setup_cfg)
        if ret:
            raise ret

        checkout_mgr = ComponentCheckoutManager(setup_config=setup_cfg)

        # This thread is necessary to notify the api endpoints and to not block the main thread
        def run_background_thread(component_checkout_mgr: ComponentCheckoutManager, component: ComponentIdentifiers,
                                  additional_name: str | None, exec_loop):
            async def set_state(state: ComponentState):
                if component == ComponentIdentifiers.CFG_UE:
                    await api_status.set_ue_status(additional_name, state)
                else:
                    await api_status.set_component_status(component, state)

            asyncio.run_coroutine_threadsafe(set_state(ComponentState.CHECKING_OUT), exec_loop)
            ret_val = False
            err_str = f"Component {component} not found!"
            match component:
                case ComponentIdentifiers.CFG_NEAR_RT_RIC:
                    ret_val = component_checkout_mgr.checkout_ric()
                case ComponentIdentifiers.CFG_5GC:
                    ret_val = component_checkout_mgr.checkout_5g_core()
                case ComponentIdentifiers.CFG_GNB:
                    ret_val = component_checkout_mgr.checkout_gnb()
                case ComponentIdentifiers.CFG_UE:
                    ret_val = component_checkout_mgr.checkout_ue()
                case ComponentIdentifiers.CFG_ZMQ_PROXY:
                    ret_val = True

            checkout_mgr_err = component_checkout_mgr.get_last_error()
            if len(checkout_mgr_err) > 0 and not ret_val:
                err_str = checkout_mgr_err

            if ret_val:
                asyncio.run_coroutine_threadsafe(set_state(ComponentState.CHECKED_OUT), exec_loop)
            else:
                asyncio.run_coroutine_threadsafe(api_status.add_error(err_str), exec_loop)

        # TODO Allow multiple rics, cores, etc. simultaneously
        for _ in setup_cfg.near_rt_rics:
            await asyncio.to_thread(run_background_thread, checkout_mgr,
                                    ComponentIdentifiers.CFG_NEAR_RT_RIC, None, loop)

        for _ in setup_cfg.cores_5g:
            await asyncio.to_thread(run_background_thread, checkout_mgr,
                                    ComponentIdentifiers.CFG_5GC, None, loop)

        for _ in setup_cfg.gnbs:
            await asyncio.to_thread(run_background_thread, checkout_mgr,
                                    ComponentIdentifiers.CFG_GNB, None, loop)

        for ue in setup_cfg.ue.ues:
            await asyncio.to_thread(run_background_thread, checkout_mgr,
                                    ComponentIdentifiers.CFG_UE, ue.name, loop)

        await asyncio.to_thread(run_background_thread, checkout_mgr,
                                ComponentIdentifiers.CFG_ZMQ_PROXY, None, loop)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to checkout repositories: {e}")


def run_build(component: Optional[ComponentIdentifiers], setup_cfg: SetupConfiguration, api_status: APIStatus,
              loop, build_all: bool = False) -> bool:
    """Executes component-specific build steps and updates API status on failure."""
    patch_firmware(setup_cfg)
    build_runner = BuildRunner(setup_configuration=setup_configuration)

    if component == ComponentIdentifiers.CFG_NEAR_RT_RIC or build_all:
        api_queue_ric = api_status.get_log_queue(ComponentIdentifiers.CFG_NEAR_RT_RIC.value)
        asyncio.run_coroutine_threadsafe(
            api_status.set_component_status(ComponentIdentifiers.CFG_NEAR_RT_RIC, ComponentState.BUILDING), loop)
        if not build_runner.build_ric(api_queue_ric):
            asyncio.run_coroutine_threadsafe(
                api_status.set_component_status(ComponentIdentifiers.CFG_NEAR_RT_RIC, ComponentState.BUILD_FAILED),
                loop)
            logging.error("build_ric returned an error")
            return False
        else:
            asyncio.run_coroutine_threadsafe(
                api_status.set_component_status(ComponentIdentifiers.CFG_NEAR_RT_RIC, ComponentState.BUILT), loop)

        if component == ComponentIdentifiers.CFG_5GC or build_all:
            api_queue_5gc = api_status.get_log_queue(ComponentIdentifiers.CFG_5GC.value)
            asyncio.run_coroutine_threadsafe(
                api_status.set_component_status(ComponentIdentifiers.CFG_5GC, ComponentState.BUILDING), loop)
            if not build_runner.build_5g_core(api_queue_5gc):
                asyncio.run_coroutine_threadsafe(api_status.set_component_status(ComponentIdentifiers.CFG_5GC,
                                                                                 ComponentState.BUILD_FAILED), loop)
                logging.error("build_5g_core returned an error")
                return False
            else:
                asyncio.run_coroutine_threadsafe(
                    api_status.set_component_status(ComponentIdentifiers.CFG_5GC, ComponentState.BUILT), loop)

        if component == ComponentIdentifiers.CFG_GNB or build_all:
            api_queue_gnb = api_status.get_log_queue(ComponentIdentifiers.CFG_GNB.value)
            asyncio.run_coroutine_threadsafe(
                api_status.set_component_status(ComponentIdentifiers.CFG_GNB, ComponentState.BUILDING), loop)
            if not build_runner.build_gnb(api_queue_gnb):
                asyncio.run_coroutine_threadsafe(
                    api_status.set_component_status(ComponentIdentifiers.CFG_GNB, ComponentState.BUILD_FAILED), loop)
                logging.error("build_gnb returned an error")
                return False
            else:
                asyncio.run_coroutine_threadsafe(
                    api_status.set_component_status(ComponentIdentifiers.CFG_GNB, ComponentState.BUILT), loop)

        if component == ComponentIdentifiers.CFG_NEAR_RT_RIC.CFG_UE or build_all:
            log_buffer_list = [api_status.get_log_queue(ue_inst.name) for ue_inst in setup_cfg.ue.ues]

            async def set_all_ue_states(state: ComponentState):
                for ue_inst in setup_cfg.ue.ues:
                    await api_status.set_ue_status(ue_inst.name, state)

            asyncio.run_coroutine_threadsafe(set_all_ue_states(ComponentState.BUILDING), loop)
            if build_runner.build_ues(log_buffer_list):  # TODO queue for each separate ue build
                logging.error("build_ues returned an error")
                for _ in setup_cfg.ue.ues:
                    asyncio.run_coroutine_threadsafe(set_all_ue_states(ComponentState.BUILD_FAILED), loop)
                    return False
            else:
                asyncio.run_coroutine_threadsafe(set_all_ue_states(ComponentState.BUILT), loop)
    return True


def format_time_difference(total_seconds: int) -> str:
    """
    Turns a timedelta object into a representation of HH-MM-SS.
    """
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}-{minutes}-{seconds}"
