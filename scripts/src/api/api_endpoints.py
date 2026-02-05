"""
This module contains all API endpoints which are provided via FastAPI.
"""

import asyncio
import datetime
import json
import logging
from typing import Literal, Any

import uvicorn
from fastapi import Request, status, HTTPException, WebSocket
from fastapi.background import BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse

from api.api_state import ComponentState, APIStateEnum, LogQueue
from api.api_utils import check_configuration, StatusResponse, run_checkout, run_build, \
    APIConfig, format_time_difference
from api.meta_data import API_IP, API_PORT, API_VERSION, AGENT_NAME, MAX_API_QUEUE_LEN
from model.core_config import Core5GCfg
from model.gnb_config import GNBCfg
from model.ric_config import NearRtRICCFG
from model.setup_configuration import ComponentIdentifiers
from model.ue_config import UECfg, UEInstCfg
from model.zmq_proxy_config import ZMQProxyCfg

api_config = APIConfig()
app = api_config.get_app()


@app.get("/", summary="Landing page")
async def root(request: Request):
    """
    Just show a landing page that points to the CipherCell Configurator documentation.
    """
    logging.debug("Requested '/' -> return landing page")
    return api_config.get_templates().TemplateResponse(
        "index.html",
        {"request": request, "title": "API Landing Page", "version": API_VERSION}
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def get_health_status():
    """
    Get Health Status of the API. Used to verify that the API is running and
    to verify the version of the API.
    """

    health_status = {"status": api_config.get_api_status().get_current_state(),
                     "last_error": api_config.get_api_status().get_last_error(),
                     "service": AGENT_NAME,
                     "version": API_VERSION,
                     "uptime": format_time_difference(
                         int((datetime.datetime.now() - api_config.get_up_time()).total_seconds())),
                     "timestamp": datetime.datetime.now().strftime("%H-%M-%S.%f")}
    logging.debug("Return health status: %s", health_status)
    return health_status


@app.get("/status", status_code=status.HTTP_200_OK)
async def get_status():
    """
    Get the current status of the API. The message contains the API status,
    the state of different components, such as additional information such
    as if all repositories are checked out.
    """
    status_msg = api_config.get_api_status().to_dict()
    status_msg["uptime"] = format_time_difference(
        int((datetime.datetime.now() - api_config.get_up_time()).total_seconds()))
    status_msg["timestamp"] = datetime.datetime.now().strftime("%H-%M-%S.%f")
    status_msg['repositories_checked_out'] = api_config.get_api_status().get_repository_state()
    logging.debug("Return status message: %s", status_msg)
    return status_msg


# Configuration functions

async def _process_component_config(config: Any, component_type: ComponentIdentifiers):
    """
    Helper function which does some basic checks, sets the API status,
    initializes the logging queue and set the configuration.
    """
    if config.implementation is None:
        await api_config.get_api_status().add_error(
            f"Invalid {component_type.value} config object parsed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{component_type.value} implementation must be set")

    setup_config = api_config.get_setup_config()
    api_status = api_config.get_api_status()
    api_status.add_log_queue(component_type.value,
                             LogQueue(queue_size=MAX_API_QUEUE_LEN))

    match component_type:
        case ComponentIdentifiers.CFG_GNB:
            setup_config.gnbs.append(config)
            setup_config.environment.gnb_implementation = config.implementation
        case ComponentIdentifiers.CFG_5GC:
            api_config.get_setup_config().cores_5g.append(config)
            api_config.get_setup_config().environment.core_implementation = config.implementation
        case ComponentIdentifiers.CFG_NEAR_RT_RIC:
            api_config.get_setup_config().near_rt_rics.append(config)
            api_config.get_setup_config().environment.ric_implementation = config.implementation
        case _:
            raise ValueError(f"Unknown component type: {component_type}")

    await api_config.get_api_status().set_component_status(component_type,
                                                           ComponentState.CONFIGURED)
    logging.debug("Set %s config: %s", component_type.value, config)


@app.post("/gnb-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_gnb_config(config: GNBCfg):
    """
    Endpoint to add the configuration of a single gNB.
    """
    await _process_component_config(config, ComponentIdentifiers.CFG_GNB)
    return StatusResponse(status=APIStateEnum.OK.value)


@app.put("/core5g-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_5g_core_config(config: Core5GCfg):
    """
    Endpoint to set the configuration of the 5G core network.
    """
    await _process_component_config(config, ComponentIdentifiers.CFG_5GC)
    return StatusResponse(status=APIStateEnum.OK.value)


@app.post("/near-rt-ric-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_near_rt_ric_config(config: NearRtRICCFG):
    """
    Endpoint to set the configuration of the 5G core network.
    """
    await _process_component_config(config, ComponentIdentifiers.CFG_NEAR_RT_RIC)
    return StatusResponse(status=APIStateEnum.OK.value)


@app.put("/ue-config-list", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_ue_config_list(ue_cfg: UECfg):
    """
    Add an entire List of UE configs.
    """
    api_config.get_setup_config().ue = ue_cfg

    if ue_cfg.ip_range is None or ue_cfg.gateway is None:
        await api_config.get_api_status().add_error("UE IP Range or Gateway not set")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UE IP Range or Gateway not set")

    for ue_inst in ue_cfg.ues:
        api_config.get_api_status().add_log_queue(ue_inst.name,
                                                  LogQueue(queue_size=MAX_API_QUEUE_LEN))
        await api_config.get_api_status().set_ue_status(ue_inst.name, ComponentState.CONFIGURED)
    logging.debug("Set UE-config: %s", ue_cfg)
    return StatusResponse(status=APIStateEnum.OK.value)


@app.post("/ue-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_ue_config(ue_inst: UEInstCfg):
    """
    Add a single UE configuration to the list of UEs.
    """
    if api_config.get_setup_config().ue is None:
        await api_config.get_api_status().add_error(
            "UE configuration list is not initialized. Run ue-config-list first.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="UE configuration list is "
                                   "not initialized. Run ue-config-list first.")

    api_config.get_setup_config().ue.ues.append(ue_inst)
    api_config.get_api_status().add_log_queue(ue_inst.name, LogQueue(queue_size=MAX_API_QUEUE_LEN))
    await api_config.get_api_status().set_ue_status(ue_inst.name, ComponentState.CONFIGURED)
    logging.debug("Add single UE: %s", ue_inst)
    return StatusResponse(status=APIStateEnum.OK.value)


@app.put("/zmq-proxy-config", response_model=StatusResponse, status_code=status.HTTP_200_OK)
async def set_zmq_proxy_config(zmq_proxy_cfg: ZMQProxyCfg):
    """
    Add a single UE configuration to the list of UEs
    """
    if zmq_proxy_cfg.ip_addr is None or zmq_proxy_cfg.component_proxy_cfgs is None:
        await api_config.get_api_status().add_error("IP or proxy configuration for "
                                                    "ZMQ Proxy not set")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="IP or proxy configuration for ZMQ Proxy not set")

    api_config.get_api_status().add_log_queue(ComponentIdentifiers.CFG_ZMQ_PROXY.value,
                                              LogQueue(queue_size=MAX_API_QUEUE_LEN))
    await api_config.get_api_status().set_component_status(ComponentIdentifiers.CFG_ZMQ_PROXY,
                                                           ComponentState.CONFIGURED)
    api_config.get_setup_config().zmq_proxy = zmq_proxy_cfg
    logging.debug("Set ZMQ Proxy settings: %s", zmq_proxy_cfg)
    return StatusResponse(status=APIStateEnum.OK.value)


@app.post("/checkout-repositories", status_code=status.HTTP_200_OK)
async def checkout_repositories(background_tasks: BackgroundTasks):
    """
    Checkout all required repositories based on the current setup configuration.
    """
    if api_config.get_api_status().get_repository_state() == ComponentState.CHECKED_OUT:
        logging.info("Repositories already cloned")
        return {"status": ComponentState.CHECKED_OUT}
    logging.debug("Start cloning repositories")
    ret = check_configuration(api_config.get_setup_config())
    if ret:
        raise ret
    try:
        if api_config.get_api_status().get_repository_state() != ComponentState.CHECKED_OUT:
            background_tasks.add_task(run_checkout,
                                api_config.get_setup_config(),
                                      api_config.get_api_status(),
                                      asyncio.get_running_loop())
    except HTTPException as e:
        await (api_config.get_api_status().
               add_error(f"Failed to checkout repositories: {e}"))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to checkout repositories: {e}") from e
    return StatusResponse(status=APIStateEnum.OK.value)


@app.post("/build/{component}", status_code=status.HTTP_200_OK)
async def build_component(component: Literal["all"] |
                                     ComponentIdentifiers, background_tasks: BackgroundTasks):
    """
    Build a component or all components of a delivered configuration.
    Valid parameters are "all" to build every component or to build
    components in isolation, the following parameters are accepted:
    - near_rt_ric
    - 5gc
    - ue
    - gnb
    - zmq_proxy
    """
    logging.info("Start building components %s", component)
    if component == 'all':
        params = (
            run_build, None, api_config.get_setup_config(), api_config.get_api_status(),
            asyncio.get_running_loop(),
            True)
    else:
        try:
            component_identifier = ComponentIdentifiers(component)
            params = (
                run_build, component_identifier, api_config.get_setup_config(),
                api_config.get_api_status(), asyncio.get_running_loop(), False)
        except ValueError as e:
            await api_config.get_api_status().add_error(f"Invalid parameter returned error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Invalid parameter returned error: {e}") from e
    background_tasks.add_task(*params)
    return StatusResponse(status=APIStateEnum.OK.value)


@app.delete("/clear-errors", status_code=status.HTTP_200_OK)
async def clear_errors():
    """
    Clears the error cache.
    """
    logging.info("Clear API error buffer")
    await api_config.get_api_status().clear_errors()
    return StatusResponse(status=APIStateEnum.OK.value)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles exceptions thrown by the API.
    """
    await api_config.get_api_status().add_error(f"err: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "request": request,
            "detail": exc.errors(),  # Pydantic error details
            "body": exc.body
        }
    )


# **************************************************
# SSE endpoints to notify the frontend or a listener
# **************************************************

async def state_watcher():
    """
    Starts a state watcher which notifies, for example when a state transition occurs.
    Furthermore, it notifies registered listeners, e.g. the GUI.
    """
    while True:
        async with api_config.get_api_status().get_condition():
            await api_config.get_api_status().get_condition().wait()
            logging.debug(
                "State Change detected push state information %s",
                json.dumps(api_config.get_api_status().to_dict()),
            )
            ret_dict = api_config.get_api_status().to_dict()
            ret_dict["repositories_checked_out"] = (
                api_config.get_api_status().get_repository_state().value
            )
            yield f"data: {json.dumps(ret_dict)}\n\n"


@app.get("/register-state-watcher")
async def register_state_watcher():
    """
    Register watcher especially for state change detected, e.g. when a starting components
    transition from initializing to running.
    """
    return StreamingResponse(state_watcher(), media_type="text/event-stream")


@app.websocket("/ws/register-logging_websocket/{component}")
async def websocket_endpoint(component: str, websocket: WebSocket):
    """
    Open a websocket endpoint sending logged data from the logging queue of this application.
    Specifically the log messages from parsing and building the dedicated components.
    """
    logging.info("Register Websocket for logging component: %s", component)
    try:
        api_config.get_api_status().get_log_queue(component)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    await websocket.accept()
    try:
        log_queue = api_config.get_api_status().get_log_queue(component)
        while True:
            lines = await log_queue.retrieve_logs()
            if len(lines) > 0:
                await websocket.send_text("".join(lines))
    except (RuntimeError, KeyError, OSError) as e:
        await api_config.get_api_status().add_error(str(e))


# **************************************************
# API entry point
# **************************************************
def start_api_server():
    """
    Start the API server using Uvicorn.
    """
    logging.info("Start FastAPI server at %s:%d", API_IP, API_PORT)
    uvicorn.run(
        app,
        host=API_IP,
        port=API_PORT,
        reload=False
    )
