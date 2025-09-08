import logging
import textwrap
import threading
import time
from itertools import zip_longest

from rich.columns import Columns
from rich.live import Live
from rich.panel import Panel

from scripts.src.controller.demo_runner import DemoRunner
from scripts.src.controller.program import Program


class ComponentThreadPool:
    def __init__(self):
        self._threads: dict[str, threading.Thread] = {}
        self._programs_dict: dict[str, Program] = {}

    @staticmethod
    def run_thread(prog: Program, live_view_buffers: dict):
        prog.start()
        process = prog.get_process()
        name = prog.get_process_name()

        MAX_LINE_WIDTH = 120  # adjust depending on your terminal size

        for line in process.stdout:
            line = line.rstrip()

            # Wrap line into multiple shorter lines if necessary
            wrapped_lines = textwrap.wrap(line, MAX_LINE_WIDTH)

            if not wrapped_lines:  # ensure at least one line goes in
                wrapped_lines = [""]

            live_view_buffers[name].extend(wrapped_lines)

            # Keep only last 10 lines
            if len(live_view_buffers[name]) > 10:
                live_view_buffers[name] = live_view_buffers[name][-10:]

    def add_program(self, program: Program):
        logging.info(f"Adding program {program.name} to thread pool.")
        self._programs_dict.update({program.name: program})

    def add_thread(self, program_identifier: str, live_view_buffers: dict):
        thread = threading.Thread(target=ComponentThreadPool.run_thread,
                                  args=(self._programs_dict[program_identifier], live_view_buffers), daemon=True)
        self._threads.update({program_identifier: thread})

    def start_thread(self, program_identifier: str):
        self._threads[program_identifier].start()

    def get_thread_list(self) -> dict[str, threading.Thread]:
        return self._threads

    def get_programs_dict(self) -> dict[str, Program]:
        return self._programs_dict


class LiveConsoleViewer:
    def __init__(self, demo_runner: DemoRunner):
        self.thread_pool = ComponentThreadPool()
        programs = demo_runner.get_programs()
        logging.info(f"Add {len(programs)} to demo runner.")
        for program in programs:
            self.thread_pool.add_program(program)

    def start_live_display_loop(self):
        logging.info("Starting live console viewer...")

        buffers = {program.get_process_name(): [] for program in self.thread_pool.get_programs_dict().values()}

        for identifier in self.thread_pool.get_programs_dict().keys():
            self.thread_pool.add_thread(program_identifier=identifier, live_view_buffers=buffers)
            self.thread_pool.start_thread(program_identifier=identifier)

        def chunked(iterable, n, fillvalue=None):
            args = [iter(iterable)] * n
            return zip_longest(*args, fillvalue=fillvalue)

        programs_list = list(self.thread_pool.get_programs_dict().values())

        with Live(refresh_per_second=4) as live:
            while any(t.is_alive() for t in self.thread_pool.get_thread_list().values()):
                panels = [
                    Panel("\n".join(buffers[program.get_process_name()]), title=program.get_process_name())
                    for program in programs_list
                ]

                # Group panels into rows of 3
                rows = []
                for group in chunked(panels, 3, fillvalue=Panel("")):
                    rows.extend(group)

                live.update(Columns(rows, equal=True))

            # Final update before exit
            panels = [
                Panel("\n".join(buffers[program.get_process_name()]), title=program.get_process_name())
                for program in programs_list
            ]
            rows = []
            for group in chunked(panels, 3, fillvalue=Panel("")):
                rows.extend(group)
            live.update(Columns(rows, equal=True))
