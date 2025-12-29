from enum import Enum
from typing import List, Optional

from api.api_utils import BuildSelector


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
        self._component_states: dict[str, ComponentState] = {"gnb": ComponentState.NOT_CONFIGURED,
                                                             "core_5g": ComponentState.NOT_CONFIGURED,
                                                             "near-rt-ric": ComponentState.NOT_CONFIGURED}
        self._repositories_checked_out: RepositoryCheckoutStatus = RepositoryCheckoutStatus.NOT_CHECKED_OUT

    def get_current_state(self) -> APIStateEnum:
        return self._status

    def get_component_status(self) -> dict[str, ComponentState]:
        return self._component_states

    def set_component_status(self, component: BuildSelector, status: ComponentState):
        self._component_states[component.value] = status

    def set_ue_status(self, ue_name: str, status: ComponentState):
        self._component_states[ue_name] = status

    def add_error(self, err: str) -> None:
        self._err_list.append(err)

    def clear_errors(self) -> None:
        self._err_list.clear()

    def get_last_error(self) -> str:
        if len(self._err_list) == 0:
            return "None"
        else:
            return self._err_list[-1]

    def set_repository_state(self, repo_state: RepositoryCheckoutStatus) -> None:
        self._repositories_checked_out = repo_state

    def get_repository_state(self) -> RepositoryCheckoutStatus:
        return self._repositories_checked_out
