import logging
import asyncio
from enum import Enum
from typing import List, Optional

from model.setup_configuration import ComponentIdentifiers


class APIStateEnum(Enum):
    OK = "ok"
    ERROR = "error"


class RepositoryCheckoutStatus(Enum):
    CHECKED_OUT = "checked_out"
    NOT_CHECKED_OUT = "not_checked_out"
    FAILED = "failed"


class ComponentState(Enum):
    CONFIGURED = "configured"
    NOT_CONFIGURED = "not_configured"
    BUILDING = "building"
    BUILT = "built"
    BUILD_FAILED = "build_failed"


class APIStatus:

    def __init__(self):
        self._status: APIStateEnum = APIStateEnum.OK
        self._err_list: Optional[List[str]] = []
        self._component_states: dict[str, ComponentState] = {
            ComponentIdentifiers.CFG_GNB.value: ComponentState.NOT_CONFIGURED,
            ComponentIdentifiers.CFG_5GC.value: ComponentState.NOT_CONFIGURED,
            ComponentIdentifiers.CFG_NEAR_RT_RIC.value: ComponentState.NOT_CONFIGURED}
        self._repositories_checked_out: RepositoryCheckoutStatus = RepositoryCheckoutStatus.NOT_CHECKED_OUT
        self._condition = asyncio.Condition()

    def get_current_state(self) -> APIStateEnum:
        return self._status

    def get_component_status(self) -> dict[str, ComponentState]:
        return self._component_states

    async def set_component_status(self, component: ComponentIdentifiers, status: ComponentState):
        logging.debug("Change component state -> send notification to state watcher")
        async with self._condition:
            self._component_states[component.value] = status
            self._condition.notify_all()

    async def set_ue_status(self, ue_name: str, status: ComponentState):
        logging.debug("Change ue status -> send notification to state watcher")
        async with self._condition:
            self._component_states[ue_name] = status
            self._condition.notify_all()

    async def add_error(self, err: str) -> None:
        logging.debug("An error occurred -> send notification to state watcher")
        async with self._condition:
            self._err_list.append(err)
            self._condition.notify_all()

    async def clear_errors(self) -> None:
        async with self._condition:
            self._err_list.clear()
            self._condition.notify_all()

    def get_last_error(self) -> str:
        if len(self._err_list) == 0:
            return "None"
        else:
            return self._err_list[-1]

    async def set_repository_state(self, repo_state: RepositoryCheckoutStatus) -> None:
        async with self._condition:
            self._condition.notify_all()
            self._repositories_checked_out = repo_state

    def get_repository_state(self) -> RepositoryCheckoutStatus:
        return self._repositories_checked_out

    def to_dict(self) -> dict:
        return {"api_status": self._status,
                "last_error": self.get_last_error(),
                "component_states": {comp: state.value for comp, state in
                                     self.get_component_status().items()},
                "repositories_checked_out": self._repositories_checked_out.value,
                }

    def get_condition(self):
        return self._condition
