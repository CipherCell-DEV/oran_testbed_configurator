import collections
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


class LogQueue:
    """
    Class storing logging information in queues of a maximum size. It implements a functionality to set
    events in order to notify the webservices communicating with the frontend.
    """
    def __init__(self, queue_size: int, flush_every: int = 1):
        self._queue = collections.deque(maxlen=queue_size)
        self._flush_sequence = flush_every
        # Async components
        self._loop = asyncio.get_running_loop()
        self._event = asyncio.Event()
        self._condition = asyncio.Condition()

    def add_element(self, message: str):
        """
        Adds a log entry. If a certain flush sequence is reached notify the websocket handler
        """
        self._queue.append(message)
        if len(self._queue) >= self._flush_sequence:
            self._loop.call_soon_threadsafe(self._event.set)

    async def retrieve_logs(self) -> list[str]:
        """
        Function called by the websockets, pauses until the data available event is set.
        Returns a list of the most recent log files.
        """
        await self._event.wait()

        self._event.clear()

        logs_to_send = list(self._queue)
        self._queue.clear()
        return logs_to_send


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
        self._api_queues: dict[str, LogQueue] = {}

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
        return {"api_status": self._status.value,
                "last_error": self.get_last_error(),
                "component_states": {comp: state.value for comp, state in
                                     self.get_component_status().items()},
                "repositories_checked_out": self._repositories_checked_out.value,
                }

    def get_condition(self):
        return self._condition

    def add_log_queue(self, identifier: str, api_queue: LogQueue):
        self._api_queues[identifier] = api_queue

    def get_log_queue(self, identifier: str) -> LogQueue:
        if identifier in self._api_queues:
            return self._api_queues[identifier]
        else:
            raise KeyError(f"Log queue entry '{identifier} does not exist")
