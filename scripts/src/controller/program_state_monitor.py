import logging
import threading
import time
from typing import Dict, Tuple, List

from demo_config import DemoProgramGroup, ProgramGroupIdentifier
from model.utils_config import ProgramState
from model.setup_configuration import SetupConfiguration
from model.demo_config import DemoProgram

WATCHDOG_JOIN_TIMEOUT_IN_S = 5
DEFAULT_RESTART_TIMEOUT_IN_S = 10
DEFAULT_MAX_NUM_RESTARTS = 1
# Wait within the watchdog loop to avoid busy waiting
DEFAULT_WATCHDOG_TIME_SLICE_IN_S = 1


class ProgramStateMonitor:
    """
    A helper class to monitor the state of a running program (RIC, Core, gNB, UE)
    and transition between states based on input logs.

    It also provides a watchdog thread that triggers a restart if the
    program stays too long in a specific state (e.g., INITIALIZING).
    """

    def __init__(self, program_group : DemoProgramGroup,
                 program_data : DemoProgram,
                 restart_timeout_in_s: int = DEFAULT_RESTART_TIMEOUT_IN_S,
                 max_num_restarts : int = DEFAULT_MAX_NUM_RESTARTS,
                 watchdog_slice: int = DEFAULT_WATCHDOG_TIME_SLICE_IN_S):
        self._program_group = program_group
        self._program_data = program_data
        self._restart_timeout_s = restart_timeout_in_s
        self._max_num_restarts = max_num_restarts
        self._watchdog_slice = watchdog_slice

        self._current_state: ProgramState = ProgramState.STOPPED
        self._state_transition_ts = 0.0
        self._last_ts = 0.0

        self._watchdog_thread = None
        self._watchdog_thread_running = False
        self._lock = threading.Lock()

        self._triggers: Dict[Tuple[ProgramGroupIdentifier, ProgramState], List[Tuple[str, ProgramState]]] = {
            # RIC
            (ProgramGroupIdentifier.RIC, ProgramState.STOPPED): [
                ("Running", ProgramState.INITIALIZING)
            ],
            (ProgramGroupIdentifier.RIC, ProgramState.INITIALIZING): [
                ("RMR is ready now ...", ProgramState.RUNNING)
            ],

            # 5G Core
            (ProgramType.CORE, ProgramState.STOPPED): [
                ("open5gs_5gc", ProgramState.INITIALIZING)
            ],
            (ProgramType.CORE, ProgramState.INITIALIZING): [
                ("UDR initialize...done", ProgramState.RUNNING)
            ],

            # gNB
            (ProgramType.GNB, ProgramState.STOPPED): [
                ("--== srsRAN", ProgramState.INITIALIZING)
            ],
            (ProgramType.GNB, ProgramState.INITIALIZING): [
                ("==== gNB started ===", ProgramState.RUNNING)
            ],

            # UE #TODO (currently only first UE supported)
            (ProgramType.UE, ProgramState.STOPPED): [
                ("Attaching to ue", ProgramState.INITIALIZING)
            ],
            (ProgramType.UE, ProgramState.INITIALIZING): [
                ("PDU Session Establishment successful.", ProgramState.RUNNING)
            ],
        }

    def _perform_state_transition(self, previous: ProgramState, next_state: ProgramState) -> bool:
        """
        Safely perform a state transition if current state matches the expected previous state.
        Returns True if successful, False otherwise.
        """
        with self._lock:
            if self._current_state != previous:
                logging.error(f"{self._program_type}: Invalid transition attempt "
                              f"from {self._current_state} (expected {previous})")
                return False
            logging.info(f"{self._program_type}: Transition {previous} -> {next_state}")
            self._current_state = next_state
            self._state_transition_ts = time.time()
            self._last_ts = self._state_transition_ts
            return True

    def get_current_state(self) -> ProgramState:
        with self._lock:
            return self._current_state

    def analyze_input_stream(self, input_stream: str):
        """
        Analyze a log line (input stream) and check whether it matches a known trigger.
        If a trigger is found, perform the corresponding state transition.
        """
        error_indication = ["error", "Error", "ERROR", "fail", "Fail"]
        if any(i in input_stream for i in error_indication):
        	logging.error(f"{input_stream}")
        key = (self._program_type, self.get_current_state())
        for trigger, next_state in self._triggers.get(key, []):
            if trigger in input_stream:
                if not self._perform_state_transition(key[1], next_state):
                    raise Exception("Error incorrect state transition")
                if self._current_state == ProgramState.RUNNING:
                    logging.info(f"{self._program_type}: started successfully ✅")
                    print()

    def watchdog_function(self):
        """
        Background watchdog loop.
        Periodically checks if the program has exceeded the allowed time in a state.
        If so, transitions to TRIGGER_RESTART.
        """
        while self._watchdog_thread_running:
            time.sleep(self._watchdog_slice)
            now = time.time()
            with self._lock:
                if self._current_state not in (ProgramState.TRIGGER_RESTART, ProgramState.STOPPED):
                    if now - self._state_transition_ts > self._restart_timeout_s:
                        self._current_state = ProgramState.TRIGGER_RESTART
                        logging.warning(
                            f"{self._program_type}: Watchdog timeout ({self._restart_timeout_s}s). "
                            f"Triggering restart. Last transition at "
                            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._state_transition_ts))}"
                        )

    def start_watchdog_thread(self):
        """
        Start the watchdog monitoring thread.
        """
        if self._watchdog_thread_running:
            logging.warning("Watchdog thread already running.")
            return
        logging.info("Starting watchdog thread...")
        self._watchdog_thread_running = True
        self._watchdog_thread = threading.Thread(
            target=self.watchdog_function, daemon=True
        )
        self._watchdog_thread.start()

    def stop_watchdog_thread(self):
        """
        Stop the watchdog thread and wait for it to exit cleanly.
        """
        if not self._watchdog_thread_running:
            logging.warning("Watchdog thread not running.")
            return
        logging.info("Stopping watchdog thread...")
        self._watchdog_thread_running = False
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=WATCHDOG_JOIN_TIMEOUT_IN_S)
            self._watchdog_thread = None
        logging.info("Watchdog thread stopped cleanly.")
