#import logging
#import signal
#import subprocess
#import textwrap
#import threading
#import time
#from itertools import zip_longest
#
#from rich.columns import Columns
#from rich.live import Live
#from rich.panel import Panel
#
#from controller.demo_runner import DemoRunner
#from controller.program import Program
#from controller.program_state_monitor import ProgramState
#from model.utils_config import MAX_DISPLAY_LINE_LENGTH
#
#NR_LINES_IN_LIVE_VIEW = 10
#
## Avoid busy waiting when checking if a component is in running state
#WAIT_BETWEEN_STATE_CHECKS_IN_S = 1
#
#
#class ComponentThreadPool:
#    def __init__(self):
#        self._threads: dict[str, threading.Thread] = {}
#        self._programs_dict: dict[str, Program] = {}
#
#    @staticmethod
#    def run_thread(prog: Program, live_view_buffers: dict):
#        prog.start()
#        process_state_checker = prog.get_program_state_checker()
#        process = prog.get_process()
#        name = prog.get_process_name()
#
#        for line in process.stdout:
#            line = str(line.rstrip())
#            process_state_checker.analyze_input_stream(line)
#            wrapped_lines = textwrap.wrap(line, MAX_DISPLAY_LINE_LENGTH)
#
#            if not wrapped_lines:
#                wrapped_lines = [""]
#
#            live_view_buffers[name].extend(wrapped_lines)
#
#            if len(live_view_buffers[name]) > NR_LINES_IN_LIVE_VIEW:
#                live_view_buffers[name] = live_view_buffers[name][-NR_LINES_IN_LIVE_VIEW:]
#
#    def add_program(self, program: Program):
#        logging.info(f"Adding program {program.name} to thread pool.")
#        self._programs_dict.update({program.name: program})
#
#    def add_thread(self, program_identifier: str, live_view_buffers: dict):
#        thread = threading.Thread(target=ComponentThreadPool.run_thread,
#                                  args=(self._programs_dict[program_identifier], live_view_buffers), daemon=True)
#        self._threads.update({program_identifier: thread})
#
#    def start_thread(self, program_identifier: str):
#        self._threads[program_identifier].start()
#
#    def get_thread_list(self) -> dict[str, threading.Thread]:
#        return self._threads
#
#    def get_programs_dict(self) -> dict[str, Program]:
#        return self._programs_dict
#
#
#class LiveConsoleViewer:
#    def __init__(self, demo_runner: DemoRunner):
#        self.thread_pool = ComponentThreadPool()
#        self.demo_runner = demo_runner
#        programs = demo_runner.get_programs()
#        logging.info(f"Add {len(programs)} to demo runner.")
#
#        self.thread_pool.add_program(programs['ric'])
#        self.thread_pool.add_program(programs['5g_core'])
#        self.thread_pool.add_program(programs['gnb'])
#        self.thread_pool.add_program(programs['ue'][0])  # TODO support multiple UEs
#
#        signal.signal(signal.SIGINT, self._signal_handler)
#        signal.signal(signal.SIGTERM, self._signal_handler)
#
#    def _signal_handler(self, signum, frame):
#        """Handle SIGINT (Ctrl+C) and SIGTERM to gracefully shutdown all containers."""
#        logging.info(f"Received signal {signum}. Stopping all containers...")
#        self._cleanup_containers()
#        exit(0)
#
#    def _cleanup_containers(self):
#        """Stop all Docker containers using docker compose down."""
#        working_dir = self.demo_runner.cfg.environment.build_dir
#
#        try:
#            logging.info("Stopping all Docker containers...")
#            result = subprocess.run(
#                ["docker", "compose", "down"],
#                cwd=working_dir,
#                capture_output=True,
#                text=True,
#                timeout=30
#            )
#
#            if result.returncode == 0:
#                logging.info("All containers stopped successfully.")
#            else:
#                logging.warning(f"Docker compose down returned non-zero exit code: {result.returncode}")
#                logging.warning(f"stderr: {result.stderr}")
#        except subprocess.TimeoutExpired:
#            logging.error("Timeout while stopping containers. Forcing container termination...")
#            subprocess.run(["docker", "compose", "kill"], cwd=working_dir, capture_output=True)
#        except Exception as e:
#            logging.error(f"Error stopping containers: {e}")
#
#    def start_live_display_loop(self):
#        logging.info("Starting live console viewer...")
#
#        buffers = {program.get_process_name(): [] for program in self.thread_pool.get_programs_dict().values()}
#
#        def wait_until_component_is_up(identifier: str):
#            current_state = ProgramState.STOPPED
#            while current_state != ProgramState.RUNNING:
#                current_state = self.thread_pool.get_programs_dict()[identifier].get_current_state()
#                time.sleep(WAIT_BETWEEN_STATE_CHECKS_IN_S)
#
#        try:
#            self.thread_pool.add_thread(program_identifier='RIC', live_view_buffers=buffers)
#            self.thread_pool.start_thread(program_identifier='RIC')
#            wait_until_component_is_up('RIC')
#
#            self.thread_pool.add_thread(program_identifier='5G-core', live_view_buffers=buffers)
#            self.thread_pool.start_thread(program_identifier='5G-core')
#            wait_until_component_is_up('5G-core')
#
#            self.thread_pool.add_thread(program_identifier='gNB', live_view_buffers=buffers)
#            self.thread_pool.start_thread(program_identifier='gNB')
#            wait_until_component_is_up('gNB')
#
#            # TODO allow multiple UEs
#            self.thread_pool.add_thread(program_identifier='UE-ue1', live_view_buffers=buffers)
#            self.thread_pool.start_thread(program_identifier='UE-ue1')
#            wait_until_component_is_up('UE-ue1')
#
#            def chunked(iterable, n, fillvalue=None):
#                args = [iter(iterable)] * n
#                return zip_longest(*args, fillvalue=fillvalue)
#
#            programs_list = list(self.thread_pool.get_programs_dict().values())
#
#            with Live(refresh_per_second=4) as live:
#                while any(t.is_alive() for t in self.thread_pool.get_thread_list().values()):
#                    panels = [
#                        Panel("\n".join(buffers[program.get_process_name()]), title=program.get_process_name())
#                        for program in programs_list
#                    ]
#
#                    # Group panels into rows of 3
#                    rows = []
#                    for group in chunked(panels, 3, fillvalue=Panel("")):
#                        rows.extend(group)
#
#                    live.update(Columns(rows, equal=True))
#
#                # Final update before exit
#                panels = [
#                    Panel("\n".join(buffers[program.get_process_name()]), title=program.get_process_name())
#                    for program in programs_list
#                ]
#                rows = []
#                for group in chunked(panels, 3, fillvalue=Panel("")):
#                    rows.extend(group)
#                live.update(Columns(rows, equal=True))
#
#        finally:
#            # Always cleanup containers when exiting
#            logging.info("Live display loop ended. Cleaning up containers...")
#            self._cleanup_containers()
