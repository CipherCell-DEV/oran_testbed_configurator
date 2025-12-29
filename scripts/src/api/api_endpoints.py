import datetime
import logging

import uvicorn
from fastapi import Request, status, HTTPException
from fastapi.background import BackgroundTasks
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from api.api_state import ComponentState, APIStateEnum
from api.api_utils import check_configuration, StatusResponse, APIStatus, \
    setup_fast_api, setup_default_setup_configuration, run_checkout, RepositoryCheckoutStatus, run_build, \
    BuildSelector, format_time_difference
from api.meta_data import API_IP, API_PORT, API_VERSION, AGENT_NAME
from model.core_config import Core5GCfg
from model.gnb_config import GNBCfg
from model.ric_config import NearRtRICCFG
from model.ue_config import UECfg, UEInstCfg
from model.zmq_proxy_config import ZMQProxyCfg

app, templates = setup_fast_api()
setup_configuration = setup_default_setup_configuration()
api_status = APIStatus()
up_time = datetime.datetime.now()


@app.get("/", summary="Landing page")
async def root(request: Request):
    """
    Just show a landing page that points to the CipherCell Configurator documentation.
    """
    logging.debug("Requested '/' -> return landing page")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "API Landing Page", "version": API_VERSION}
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def get_health_status():
    """
    Get Health Status of the API. Used to verify that the API is running and
    to verify the version of the API.
    """

    health_status = {"status": api_status.get_current_state(),
                     "last_error": api_status.get_last_error(),
                     "service": AGENT_NAME,
                     "version": API_VERSION,
                     "uptime": format_time_difference(int((datetime.datetime.now() - up_time).total_seconds())),
                     "timestamp": datetime.datetime.now().strftime("%H-%M-%S.%f")}
    logging.debug(f"Return health status: {health_status}")
    return health_status


@app.get("/status", status_code=status.HTTP_200_OK)
async def get_status():
    """
    Get the current status of the API. The message contains the API status, the state of different components, such
    as additional information such as if all repositories are checked out.
    """
    status_msg = {"api_status": api_status.get_current_state(),
                  "last_error": api_status.get_last_error(),
                  "component_states": {comp: state.value for comp, state in api_status.get_component_status().items()},
                  "repositories_checked_out": api_status.get_repository_state().value,
                  "uptime": format_time_difference(int((datetime.datetime.now() - up_time).total_seconds())),
                  "timestamp": datetime.datetime.now().strftime("%H-%M-%S.%f")
                  }
    logging.debug(f"Return status message: {status_msg}")
    return status_msg


@app.post("/gnb-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_gnb_config(config: GNBCfg):
    """
    Endpoint to add the configuration of a single gNB.
    """
    if config.implementation is None:
        api_status.add_error("Invalid GNBCfg object parsed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GNBCfg implementation must be set")

    setup_configuration.gnbs.append(config)
    setup_configuration.environment.gnb_implementation = config.implementation
    api_status.set_component_status(BuildSelector.GNB, ComponentState.CONFIGURED)
    logging.debug(f"Set gNB config: {config}")
    return StatusResponse(status=APIStateEnum.OK)


@app.put("/core5g-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_5g_core_config(config: Core5GCfg):
    """
    Endpoint to set the configuration of the 5G core network.
    """
    if config.implementation is None:
        api_status.add_error("Invalid Core5GCfg object parsed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Core5GCfg implementation must be set")

    setup_configuration.cores_5g.append(config)
    setup_configuration.environment.core_implementation = config.implementation
    api_status.set_component_status(BuildSelector.CORE_5G, ComponentState.CONFIGURED)
    logging.debug(f"Set 5G-core config: {config}")
    return StatusResponse(status=APIStateEnum.OK)


@app.post("/near-rt-ric-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_near_rt_ric_config(config: NearRtRICCFG):
    """
    Endpoint to set the configuration of the 5G core network.
    """
    if config.implementation is None:
        api_status.add_error("Invalid NearRtRICCFG object parsed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NearRtRICCFG implementation must be set")

    setup_configuration.near_rt_rics.append(config)
    setup_configuration.environment.ric_implementation = config.implementation
    api_status.set_component_status(BuildSelector.RIC, ComponentState.CONFIGURED)
    logging.debug(f"Set near-rt-ric config: {config}")
    return StatusResponse(status=APIStateEnum.OK)


@app.put("/ue-config-list", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_ue_config_list(ue_cfg: UECfg):
    """
    Add an entire List of UE configs.
    """
    setup_configuration.ue = ue_cfg

    if ue_cfg.ip_range is None or ue_cfg.gateway is None:
        api_status.add_error("UE IP Range or Gateway not set")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UE IP Range or Gateway not set")

    for ue in ue_cfg.ues:
        api_status.set_ue_status(ue.name, ComponentState.CONFIGURED)
    logging.debug(f"Set UE-config: {ue_cfg}")
    return StatusResponse(status=APIStateEnum.OK)


@app.post("/ue-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_ue_config(ue_inst: UEInstCfg):
    """
    Add a single UE configuration to the list of UEs.
    """
    if setup_configuration.ue is None:
        api_status.add_error("UE configuration list is not initialized. Run ue-config-list first.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="UE configuration list is not initialized. Run ue-config-list first.")

    setup_configuration.ue.ues.append(ue_inst)
    api_status.set_ue_status(ue_inst.name, ComponentState.CONFIGURED)
    logging.debug(f"Add single UE: {ue_inst}")
    return StatusResponse(status=APIStateEnum.OK)


@app.put("/zmq-proxy-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_zmq_proxy_config(zmq_proxy_cfg: ZMQProxyCfg):
    """
    Add a single UE configuration to the list of UEs
    """
    if zmq_proxy_cfg.ip_addr is None or zmq_proxy_cfg.component_proxy_cfgs is None:
        api_status.add_error("IP or proxy configuration for ZMQ Proxy not set")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="IP or proxy configuration for ZMQ Proxy not set")

    api_status.set_component_status(BuildSelector.ZMQ_PROXY, ComponentState.CONFIGURED)
    setup_configuration.zmq_proxy = zmq_proxy_cfg
    logging.debug(f"Set ZMQ Proxy settings: {zmq_proxy_cfg}")
    return StatusResponse(status=APIStateEnum.OK)


@app.post("/checkout-repositories", status_code=status.HTTP_200_OK)
async def checkout_repositories(background_tasks: BackgroundTasks):
    """
    Checkout all required repositories based on the current setup configuration.
    """
    if api_status.set_repository_state(RepositoryCheckoutStatus.CHECKED_OUT):
        logging.info(f"Repositories already cloned")
        return {"status": RepositoryCheckoutStatus.CHECKED_OUT}
    else:
        logging.debug(f"Start cloning repositories")
        ret = check_configuration(setup_configuration)
        if ret:
            raise ret
        try:
            if api_status.get_repository_state() != RepositoryCheckoutStatus.CHECKED_OUT:
                background_tasks.add_task(run_checkout, setup_configuration, api_status)
        except Exception as e:
            api_status.add_error(f"Failed to checkout repositories: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Failed to checkout repositories: {e}")
    return StatusResponse(status=APIStateEnum.OK)


@app.post("/build/{component}", status_code=status.HTTP_200_OK)
async def build_component(component: BuildSelector, background_tasks: BackgroundTasks):
    """
    Get the current status of the API.
    """
    logging.info(f"Start building components {component}")
    background_tasks.add_task(run_build, component, setup_configuration, api_status)
    return StatusResponse(status=APIStateEnum.OK)


@app.delete("/clear-errors", status_code=status.HTTP_200_OK)
async def clear_errors():
    """
    Clears the error cache.
    """
    logging.info(f"Clear API error buffer")
    api_status.clear_errors()
    return StatusResponse(status=APIStateEnum.OK)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles exceptions
    """
    api_status.add_error(f"err: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "request": request,
            "detail": exc.errors(),  # Pydantic error details
            "body": exc.body
        }
    )


def start_api_server():
    """
    Start the API server using Uvicorn.
    """
    logging.info(f"Start FastAPI server at {API_IP}:{API_PORT}")
    uvicorn.run(
        app,
        host=API_IP,
        port=API_PORT,
        reload=False
    )
